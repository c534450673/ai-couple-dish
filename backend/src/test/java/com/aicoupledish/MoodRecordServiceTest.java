package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.MoodRecordMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.MoodRecord;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.MoodRecordDTO;
import com.aicoupledish.domain.req.MoodRecordReq;
import com.aicoupledish.service.NotificationService;
import com.aicoupledish.service.impl.MoodRecordServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 心情记录服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("心情记录服务测试")
class MoodRecordServiceTest {

    @Mock
    private MoodRecordMapper moodRecordMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private NotificationService notificationService;

    @InjectMocks
    private MoodRecordServiceImpl moodRecordService;

    private Long userId;
    private Long partnerId;
    private Long coupleId;
    private User user;
    private User partner;
    private Couple couple;

    @BeforeEach
    void setUp() {
        userId = 1L;
        partnerId = 2L;
        coupleId = 100L;

        user = new User();
        user.setId(userId);
        user.setNickName("小明");
        user.setAvatarUrl("/avatar/1.png");
        user.setCoupleId(coupleId);

        partner = new User();
        partner.setId(partnerId);
        partner.setNickName("小红");
        partner.setAvatarUrl("/avatar/2.png");

        couple = new Couple();
        couple.setId(coupleId);
        couple.setUser1Id(userId);
        couple.setUser2Id(partnerId);
    }

    private MoodRecord createMoodRecord(Long id, String moodType, Long senderId) {
        MoodRecord record = new MoodRecord();
        record.setId(id);
        record.setUserId(senderId);
        record.setCoupleId(coupleId);
        record.setMoodType(moodType);
        record.setDescription("测试心情");
        record.setMoodIcon("😊");
        record.setMoodColor("#FFD700");
        record.setRecordDate(LocalDate.now());
        record.setIsRead(0);
        record.setCreateTime(LocalDateTime.now());
        return record;
    }

    @Nested
    @DisplayName("发送心情")
    class SendMoodTest {

        @Test
        @DisplayName("发送心情-成功")
        void sendMood_Success() {
            // Given
            MoodRecordReq req = new MoodRecordReq();
            req.setMoodType("happy");
            req.setDescription("今天心情很好");

            when(userMapper.selectById(userId)).thenReturn(user);
            when(moodRecordMapper.insert(any(MoodRecord.class))).thenAnswer(invocation -> {
                MoodRecord r = invocation.getArgument(0);
                r.setId(1L);
                return 1;
            });
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);

            // When
            Long moodId = moodRecordService.sendMood(userId, req);

            // Then
            assertNotNull(moodId);
            assertEquals(1L, moodId);
            verify(moodRecordMapper).insert(argThat(r ->
                    r.getUserId().equals(userId) &&
                    r.getCoupleId().equals(coupleId) &&
                    "happy".equals(r.getMoodType()) &&
                    "😊".equals(r.getMoodIcon()) &&
                    "#FFD700".equals(r.getMoodColor()) &&
                    r.getIsRead() == 0
            ));
            verify(notificationService).sendNotification(eq(partnerId), eq(2),
                    eq("💌 心情投递"), anyString(), eq(1L), eq("mood_record"));
        }

        @Test
        @DisplayName("发送心情-未绑定情侣应抛异常")
        void sendMood_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            MoodRecordReq req = new MoodRecordReq();
            req.setMoodType("happy");

            // When & Then
            assertThrows(BusinessException.class,
                    () -> moodRecordService.sendMood(userId, req));
        }

        @Test
        @DisplayName("发送心情-无效心情类型应抛IllegalArgumentException")
        void sendMood_InvalidType() {
            // Given
            MoodRecordReq req = new MoodRecordReq();
            req.setMoodType("invalid_type");

            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> moodRecordService.sendMood(userId, req));
            assertEquals("无效的心情类型", ex.getMessage());
        }

        @Test
        @DisplayName("发送心情-用户不存在应抛异常")
        void sendMood_UserNotFound() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(null);

            MoodRecordReq req = new MoodRecordReq();
            req.setMoodType("happy");

            // When & Then
            assertThrows(BusinessException.class,
                    () -> moodRecordService.sendMood(userId, req));
        }

        @Test
        @DisplayName("发送心情-各种有效心情类型")
        void sendMood_ValidTypes() {
            String[] validTypes = {"happy", "love", "miss_you", "tired", "upset", "sad", "angry", "anxious"};

            for (String type : validTypes) {
                // Given
                MoodRecordReq req = new MoodRecordReq();
                req.setMoodType(type);

                when(userMapper.selectById(userId)).thenReturn(user);
                when(moodRecordMapper.insert(any(MoodRecord.class))).thenAnswer(invocation -> {
                    MoodRecord r = invocation.getArgument(0);
                    r.setId(1L);
                    return 1;
                });

                // When
                Long moodId = moodRecordService.sendMood(userId, req);

                // Then
                assertNotNull(moodId);
            }
        }
    }

    @Nested
    @DisplayName("获取今日心情")
    class GetTodayMoodsTest {

        @Test
        @DisplayName("获取今日心情-成功")
        void getTodayMoods_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);

            MoodRecord record = createMoodRecord(1L, "happy", userId);
            when(moodRecordMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(record));
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            List<MoodRecordDTO> result = moodRecordService.getTodayMoods(userId);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals("happy", result.get(0).getMoodType());
            assertEquals("开心", result.get(0).getMoodTypeName());
        }

        @Test
        @DisplayName("获取今日心情-未绑定情侣应抛异常")
        void getTodayMoods_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> moodRecordService.getTodayMoods(userId));
        }
    }

    @Nested
    @DisplayName("获取心情历史")
    class GetMoodHistoryTest {

        @Test
        @DisplayName("获取心情历史-成功")
        void getMoodHistory_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);

            MoodRecord record = createMoodRecord(1L, "happy", userId);
            when(moodRecordMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(record));
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            List<MoodRecordDTO> result = moodRecordService.getMoodHistory(userId, 30);

            // Then
            assertNotNull(result);
        }

        @Test
        @DisplayName("获取心情历史-默认30条")
        void getMoodHistory_DefaultLimit() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(moodRecordMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            moodRecordService.getMoodHistory(userId, null);

            // Then
            verify(moodRecordMapper).selectList(any(LambdaQueryWrapper.class));
        }

        @Test
        @DisplayName("获取心情历史-未绑定情侣应抛异常")
        void getMoodHistory_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> moodRecordService.getMoodHistory(userId, 30));
        }
    }

    @Nested
    @DisplayName("标记已读")
    class MarkAsReadTest {

        @Test
        @DisplayName("标记已读-成功")
        void markAsRead_Success() {
            // Given
            MoodRecord record = createMoodRecord(1L, "happy", partnerId);
            when(moodRecordMapper.selectById(1L)).thenReturn(record);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            moodRecordService.markAsRead(userId, 1L);

            // Then
            verify(moodRecordMapper).updateById(argThat(r ->
                    r.getIsRead() == 1 && r.getReadTime() != null
            ));
        }

        @Test
        @DisplayName("标记已读-记录不存在应抛IllegalArgumentException")
        void markAsRead_NotFound() {
            // Given
            when(moodRecordMapper.selectById(999L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> moodRecordService.markAsRead(userId, 999L));
            assertEquals("心情记录不存在", ex.getMessage());
        }

        @Test
        @DisplayName("标记已读-无权操作应抛异常")
        void markAsRead_NoPermission() {
            // Given
            MoodRecord record = createMoodRecord(1L, "happy", partnerId);
            record.setCoupleId(999L); // 不同情侣
            when(moodRecordMapper.selectById(1L)).thenReturn(record);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> moodRecordService.markAsRead(userId, 1L));
        }

        @Test
        @DisplayName("标记已读-已读不重复更新")
        void markAsRead_AlreadyRead() {
            // Given
            MoodRecord record = createMoodRecord(1L, "happy", partnerId);
            record.setIsRead(1);
            when(moodRecordMapper.selectById(1L)).thenReturn(record);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            moodRecordService.markAsRead(userId, 1L);

            // Then
            verify(moodRecordMapper, never()).updateById(any(MoodRecord.class));
        }
    }

    @Nested
    @DisplayName("获取心情统计")
    class GetMoodStatsTest {

        @Test
        @DisplayName("获取心情统计-成功")
        void getMoodStats_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(moodRecordMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(5L);

            MoodRecord happyRecord = createMoodRecord(1L, "happy", userId);
            MoodRecord loveRecord = createMoodRecord(2L, "love", partnerId);
            when(moodRecordMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Arrays.asList(happyRecord, loveRecord));

            // When
            MoodRecordDTO.MoodStats result = moodRecordService.getMoodStats(userId);

            // Then
            assertNotNull(result);
            assertEquals(5, result.getTodayCount());
            assertNotNull(result.getDistribution());
        }

        @Test
        @DisplayName("获取心情统计-未绑定情侣应抛异常")
        void getMoodStats_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> moodRecordService.getMoodStats(userId));
        }
    }

    @Nested
    @DisplayName("获取心情类型列表")
    class GetMoodTypesTest {

        @Test
        @DisplayName("获取心情类型-成功")
        void getMoodTypes_Success() {
            // When
            List<MoodRecordDTO.MoodType> result = moodRecordService.getMoodTypes();

            // Then
            assertNotNull(result);
            assertEquals(8, result.size()); // 8种心情类型
            assertEquals("happy", result.get(0).getType());
            assertEquals("开心", result.get(0).getName());
            assertEquals("😊", result.get(0).getIcon());
        }
    }

    @Nested
    @DisplayName("获取未读数量")
    class GetUnreadCountTest {

        @Test
        @DisplayName("获取未读数量-成功")
        void getUnreadCount_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(moodRecordMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(3L);

            // When
            Integer count = moodRecordService.getUnreadCount(userId);

            // Then
            assertEquals(3, count);
        }

        @Test
        @DisplayName("获取未读数量-未绑定情侣返回0")
        void getUnreadCount_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            Integer count = moodRecordService.getUnreadCount(userId);

            // Then
            assertEquals(0, count);
        }

        @Test
        @DisplayName("获取未读数量-返回0当null")
        void getUnreadCount_Null() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(moodRecordMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            Integer count = moodRecordService.getUnreadCount(userId);

            // Then
            assertEquals(0, count);
        }
    }

    @Nested
    @DisplayName("获取心情详情")
    class GetMoodDetailTest {

        @Test
        @DisplayName("获取心情详情-成功")
        void getMoodDetail_Success() {
            // Given
            MoodRecord record = createMoodRecord(1L, "happy", userId);
            when(moodRecordMapper.selectById(1L)).thenReturn(record);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            MoodRecordDTO result = moodRecordService.getMoodDetail(userId, 1L);

            // Then
            assertNotNull(result);
            assertEquals("happy", result.getMoodType());
            assertEquals("开心", result.getMoodTypeName());
        }

        @Test
        @DisplayName("获取心情详情-记录不存在应抛IllegalArgumentException")
        void getMoodDetail_NotFound() {
            // Given
            when(moodRecordMapper.selectById(999L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> moodRecordService.getMoodDetail(userId, 999L));
            assertEquals("心情记录不存在", ex.getMessage());
        }

        @Test
        @DisplayName("获取心情详情-无权查看应抛异常")
        void getMoodDetail_NoPermission() {
            // Given
            MoodRecord record = createMoodRecord(1L, "happy", userId);
            record.setCoupleId(999L);
            when(moodRecordMapper.selectById(1L)).thenReturn(record);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> moodRecordService.getMoodDetail(userId, 1L));
        }
    }
}
