package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.SweetBombDTO;
import com.aicoupledish.service.NotificationService;
import com.aicoupledish.service.impl.SweetBombServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 甜蜜炸弹服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("甜蜜炸弹服务测试")
class SweetBombServiceTest {

    @Mock
    private SweetBombMapper sweetBombMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private AnniversaryMapper anniversaryMapper;

    @Mock
    private CoupleMenuMapper coupleMenuMapper;

    @Mock
    private TimeCapsuleMapper timeCapsuleMapper;

    @Mock
    private NotificationService notificationService;

    @InjectMocks
    private SweetBombServiceImpl sweetBombService;

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
        user.setCoupleId(coupleId);

        partner = new User();
        partner.setId(partnerId);
        partner.setNickName("小红");

        couple = new Couple();
        couple.setId(coupleId);
        couple.setUser1Id(userId);
        couple.setUser2Id(partnerId);
    }

    private SweetBomb createBomb(Long id, String bombType, int isRead, int isAnswered) {
        SweetBomb bomb = new SweetBomb();
        bomb.setId(id);
        bomb.setCoupleId(coupleId);
        bomb.setBombType(bombType);
        bomb.setContent("{\"title\":\"测试炸弹\",\"description\":\"测试内容\"}");
        bomb.setSentTime(LocalDateTime.now());
        bomb.setIsRead(isRead);
        bomb.setIsAnswered(isAnswered);
        bomb.setCreateTime(LocalDateTime.now());
        return bomb;
    }

    private void mockGetCoupleByUserId() {
        when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                .thenReturn(Collections.singletonList(couple));
    }

    @Nested
    @DisplayName("生成甜蜜炸弹")
    class GenerateBombTest {

        @Test
        @DisplayName("生成炸弹-成功")
        void generateBomb_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(sweetBombMapper.insert(any(SweetBomb.class))).thenAnswer(invocation -> {
                SweetBomb b = invocation.getArgument(0);
                b.setId(1L);
                return 1;
            });
            when(coupleMapper.selectById(coupleId)).thenReturn(couple);
            // Mock data for memory/data type bombs (lenient because random bomb type may not use all stubs)
            lenient().when(anniversaryMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());
            lenient().when(coupleMenuMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(5L);
            lenient().when(anniversaryMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(2L);
            lenient().when(timeCapsuleMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(3L);

            // When
            SweetBombDTO result = sweetBombService.generateBomb(userId);

            // Then
            assertNotNull(result);
            assertNotNull(result.getId());
            assertNotNull(result.getBombType());
            verify(sweetBombMapper).insert(any(SweetBomb.class));
            verify(notificationService).sendNotification(eq(partnerId), eq(2),
                    eq("💣 甜蜜炸弹"), anyString(), eq(1L), eq("sweet_bomb"));
        }

        @Test
        @DisplayName("生成炸弹-未绑定情侣应抛异常")
        void generateBomb_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> sweetBombService.generateBomb(userId));
        }

        @Test
        @DisplayName("生成炸弹-用户不存在应抛异常")
        void generateBomb_UserNotFound() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(null);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> sweetBombService.generateBomb(userId));
        }
    }

    @Nested
    @DisplayName("获取未读炸弹")
    class GetUnreadBombsTest {

        @Test
        @DisplayName("获取未读炸弹-成功")
        void getUnreadBombs_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);

            SweetBomb bomb = createBomb(1L, "memory", 0, 0);
            when(sweetBombMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(bomb));

            // When
            List<SweetBombDTO> result = sweetBombService.getUnreadBombs(userId);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertFalse(result.get(0).getIsRead());
        }

        @Test
        @DisplayName("获取未读炸弹-未绑定情侣应抛异常")
        void getUnreadBombs_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> sweetBombService.getUnreadBombs(userId));
        }
    }

    @Nested
    @DisplayName("获取炸弹详情")
    class GetBombDetailTest {

        @Test
        @DisplayName("获取详情-成功")
        void getBombDetail_Success() {
            // Given
            SweetBomb bomb = createBomb(1L, "question", 0, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            SweetBombDTO result = sweetBombService.getBombDetail(userId, 1L);

            // Then
            assertNotNull(result);
            assertEquals(1L, result.getId());
            assertEquals("question", result.getBombType());
            assertEquals("心动问答", result.getBombTypeName());
        }

        @Test
        @DisplayName("获取详情-炸弹不存在应抛IllegalArgumentException")
        void getBombDetail_NotFound() {
            // Given
            when(sweetBombMapper.selectById(999L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> sweetBombService.getBombDetail(userId, 999L));
            assertEquals("炸弹不存在", ex.getMessage());
        }

        @Test
        @DisplayName("获取详情-无权查看应抛异常")
        void getBombDetail_NoPermission() {
            // Given
            SweetBomb bomb = createBomb(1L, "memory", 0, 0);
            bomb.setCoupleId(999L);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> sweetBombService.getBombDetail(userId, 1L));
        }
    }

    @Nested
    @DisplayName("标记炸弹已读")
    class MarkAsReadTest {

        @Test
        @DisplayName("标记已读-成功")
        void markAsRead_Success() {
            // Given
            SweetBomb bomb = createBomb(1L, "memory", 0, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            sweetBombService.markAsRead(userId, 1L);

            // Then
            verify(sweetBombMapper).updateById(argThat(b -> b.getIsRead() == 1));
        }

        @Test
        @DisplayName("标记已读-炸弹不存在应抛异常")
        void markAsRead_NotFound() {
            // Given
            when(sweetBombMapper.selectById(999L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> sweetBombService.markAsRead(userId, 999L));
            assertEquals("炸弹不存在", ex.getMessage());
        }

        @Test
        @DisplayName("标记已读-无权操作应抛异常")
        void markAsRead_NoPermission() {
            // Given
            SweetBomb bomb = createBomb(1L, "memory", 0, 0);
            bomb.setCoupleId(999L);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> sweetBombService.markAsRead(userId, 1L));
        }

        @Test
        @DisplayName("标记已读-已读不重复更新")
        void markAsRead_AlreadyRead() {
            // Given
            SweetBomb bomb = createBomb(1L, "memory", 1, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            sweetBombService.markAsRead(userId, 1L);

            // Then
            verify(sweetBombMapper, never()).updateById(any(SweetBomb.class));
        }
    }

    @Nested
    @DisplayName("回答炸弹")
    class AnswerBombTest {

        @Test
        @DisplayName("回答炸弹-成功")
        void answerBomb_Success() {
            // Given
            SweetBomb bomb = createBomb(1L, "question", 0, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            sweetBombService.answerBomb(userId, 1L, "当然愿意！");

            // Then
            verify(sweetBombMapper).updateById(argThat(b ->
                    b.getIsAnswered() == 1 &&
                    "当然愿意！".equals(b.getAnswerContent()) &&
                    b.getAnswerTime() != null
            ));
        }

        @Test
        @DisplayName("回答炸弹-非问答类型应抛IllegalArgumentException")
        void answerBomb_NotQuestionType() {
            // Given
            SweetBomb bomb = createBomb(1L, "memory", 0, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> sweetBombService.answerBomb(userId, 1L, "回答"));
            assertEquals("此炸弹不需要回答", ex.getMessage());
        }

        @Test
        @DisplayName("回答炸弹-炸弹不存在应抛异常")
        void answerBomb_NotFound() {
            // Given
            when(sweetBombMapper.selectById(999L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> sweetBombService.answerBomb(userId, 999L, "回答"));
            assertEquals("炸弹不存在", ex.getMessage());
        }

        @Test
        @DisplayName("回答炸弹-无权操作应抛异常")
        void answerBomb_NoPermission() {
            // Given
            SweetBomb bomb = createBomb(1L, "question", 0, 0);
            bomb.setCoupleId(999L);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> sweetBombService.answerBomb(userId, 1L, "回答"));
        }
    }

    @Nested
    @DisplayName("获取炸弹历史")
    class GetBombHistoryTest {

        @Test
        @DisplayName("获取历史-成功")
        void getBombHistory_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);

            SweetBomb bomb1 = createBomb(1L, "memory", 1, 0);
            SweetBomb bomb2 = createBomb(2L, "question", 1, 1);
            when(sweetBombMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Arrays.asList(bomb1, bomb2));

            // When
            List<SweetBombDTO> result = sweetBombService.getBombHistory(userId, 20);

            // Then
            assertNotNull(result);
            assertEquals(2, result.size());
        }

        @Test
        @DisplayName("获取历史-默认20条")
        void getBombHistory_DefaultLimit() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(sweetBombMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            sweetBombService.getBombHistory(userId, null);

            // Then
            verify(sweetBombMapper).selectList(any(LambdaQueryWrapper.class));
        }

        @Test
        @DisplayName("获取历史-未绑定情侣应抛异常")
        void getBombHistory_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> sweetBombService.getBombHistory(userId, 20));
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
            when(sweetBombMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(5L);

            // When
            Integer count = sweetBombService.getUnreadCount(userId);

            // Then
            assertEquals(5, count);
        }

        @Test
        @DisplayName("获取未读数量-未绑定情侣返回0")
        void getUnreadCount_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            Integer count = sweetBombService.getUnreadCount(userId);

            // Then
            assertEquals(0, count);
        }

        @Test
        @DisplayName("获取未读数量-返回0当null")
        void getUnreadCount_Null() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(sweetBombMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            Integer count = sweetBombService.getUnreadCount(userId);

            // Then
            assertEquals(0, count);
        }
    }

    @Nested
    @DisplayName("炸弹类型名称映射")
    class BombTypeNameTest {

        @Test
        @DisplayName("获取详情-回忆时光机类型名")
        void bombTypeName_Memory() {
            // Given
            SweetBomb bomb = createBomb(1L, "memory", 0, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            SweetBombDTO result = sweetBombService.getBombDetail(userId, 1L);

            // Then
            assertEquals("回忆时光机", result.getBombTypeName());
        }

        @Test
        @DisplayName("获取详情-恋爱数据站类型名")
        void bombTypeName_Data() {
            // Given
            SweetBomb bomb = createBomb(1L, "data", 0, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            SweetBombDTO result = sweetBombService.getBombDetail(userId, 1L);

            // Then
            assertEquals("恋爱数据站", result.getBombTypeName());
        }

        @Test
        @DisplayName("获取详情-节日提醒类型名")
        void bombTypeName_Festival() {
            // Given
            SweetBomb bomb = createBomb(1L, "festival", 0, 0);
            when(sweetBombMapper.selectById(1L)).thenReturn(bomb);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            SweetBombDTO result = sweetBombService.getBombDetail(userId, 1L);

            // Then
            assertEquals("节日提醒", result.getBombTypeName());
        }
    }
}
