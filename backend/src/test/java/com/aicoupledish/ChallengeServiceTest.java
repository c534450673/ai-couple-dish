package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.ChallengeDTO;
import com.aicoupledish.domain.dto.CheckinRecordDTO;
import com.aicoupledish.domain.req.CheckinReq;
import com.aicoupledish.domain.req.CreateChallengeReq;
import com.aicoupledish.service.impl.ChallengeServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 挑战服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("挑战服务测试")
class ChallengeServiceTest {

    @Mock
    private ChallengeMapper challengeMapper;

    @Mock
    private CheckinRecordMapper checkinRecordMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private ChallengeServiceImpl challengeService;

    private Long userId;
    private Long partnerId;
    private Long coupleId;
    private Couple couple;
    private User creator;
    private User partner;

    @BeforeEach
    void setUp() {
        userId = 1L;
        partnerId = 2L;
        coupleId = 100L;

        creator = new User();
        creator.setId(userId);
        creator.setNickName("小明");
        creator.setAvatarUrl("/avatar/1.png");

        partner = new User();
        partner.setId(partnerId);
        partner.setNickName("小红");
        partner.setAvatarUrl("/avatar/2.png");

        couple = new Couple();
        couple.setId(coupleId);
        couple.setUser1Id(userId);
        couple.setUser2Id(partnerId);
        couple.setStatus(1);
    }

    private void mockGetCoupleByUserId() {
        when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                .thenReturn(Collections.singletonList(couple));
    }

    private Challenge createChallenge(Long id, int status) {
        Challenge challenge = new Challenge();
        challenge.setId(id);
        challenge.setCoupleId(coupleId);
        challenge.setCreatorId(userId);
        challenge.setPartnerId(partnerId);
        challenge.setChallengeType("daily");
        challenge.setTitle("早起打卡");
        challenge.setDescription("每天早起");
        challenge.setTargetDays(7);
        challenge.setCurrentDays(0);
        challenge.setStatus(status);
        challenge.setStartDate(LocalDate.now());
        challenge.setIsDeleted(0);
        return challenge;
    }

    @Nested
    @DisplayName("创建挑战")
    class CreateChallengeTest {

        @Test
        @DisplayName("创建挑战-成功")
        void createChallenge_Success() {
            // Given
            CreateChallengeReq req = new CreateChallengeReq();
            req.setChallengeType("daily");
            req.setTitle("早起打卡");
            req.setDescription("每天早起");
            req.setTargetDays(7);

            mockGetCoupleByUserId();
            when(challengeMapper.insert(any(Challenge.class))).thenAnswer(invocation -> {
                Challenge c = invocation.getArgument(0);
                c.setId(1L);
                return 1;
            });

            // When
            Long challengeId = challengeService.createChallenge(userId, req);

            // Then
            assertNotNull(challengeId);
            assertEquals(1L, challengeId);
            verify(challengeMapper).insert(argThat(c ->
                    c.getCoupleId().equals(coupleId) &&
                    c.getCreatorId().equals(userId) &&
                    c.getPartnerId().equals(partnerId) &&
                    c.getStatus() == 0 &&
                    c.getCurrentDays() == 0
            ));
        }

        @Test
        @DisplayName("创建挑战-未绑定情侣应抛异常")
        void createChallenge_NotBound() {
            // Given
            CreateChallengeReq req = new CreateChallengeReq();
            req.setChallengeType("daily");
            req.setTitle("早起打卡");
            req.setTargetDays(7);

            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.createChallenge(userId, req));
            assertEquals("您还没有绑定情侣", ex.getMessage());
        }

        @Test
        @DisplayName("创建挑战-默认开始日期为今天")
        void createChallenge_DefaultStartDate() {
            // Given
            CreateChallengeReq req = new CreateChallengeReq();
            req.setChallengeType("daily");
            req.setTitle("早起打卡");
            req.setTargetDays(7);
            req.setStartDate(null);

            mockGetCoupleByUserId();
            when(challengeMapper.insert(any(Challenge.class))).thenAnswer(invocation -> {
                Challenge c = invocation.getArgument(0);
                c.setId(1L);
                return 1;
            });

            // When
            challengeService.createChallenge(userId, req);

            // Then
            verify(challengeMapper).insert(argThat(c ->
                    c.getStartDate().equals(LocalDate.now())
            ));
        }
    }

    @Nested
    @DisplayName("接受挑战")
    class AcceptChallengeTest {

        @Test
        @DisplayName("接受挑战-成功")
        void acceptChallenge_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then - no exception thrown
            assertDoesNotThrow(() -> challengeService.acceptChallenge(partnerId, 1L));
        }

        @Test
        @DisplayName("接受挑战-非伙伴应抛异常")
        void acceptChallenge_NotPartner() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.acceptChallenge(999L, 1L));
            assertEquals("您不是该挑战的伙伴", ex.getMessage());
        }

        @Test
        @DisplayName("接受挑战-已完成的挑战应抛异常")
        void acceptChallenge_ChallengeNotInProgress() {
            // Given
            Challenge challenge = createChallenge(1L, 1); // 已完成
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.acceptChallenge(partnerId, 1L));
            assertEquals("挑战状态不允许操作", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("拒绝挑战")
    class RejectChallengeTest {

        @Test
        @DisplayName("拒绝挑战-成功")
        void rejectChallenge_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When
            challengeService.rejectChallenge(partnerId, 1L);

            // Then
            verify(challengeMapper).updateById(argThat(c -> c.getStatus() == 3));
        }

        @Test
        @DisplayName("拒绝挑战-非伙伴应抛异常")
        void rejectChallenge_NotPartner() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.rejectChallenge(999L, 1L));
            assertEquals("您不是该挑战的伙伴", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("取消挑战")
    class CancelChallengeTest {

        @Test
        @DisplayName("取消挑战-成功")
        void cancelChallenge_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When
            challengeService.cancelChallenge(userId, 1L);

            // Then
            verify(challengeMapper).updateById(argThat(c -> c.getStatus() == 3));
        }

        @Test
        @DisplayName("取消挑战-非创建者应抛异常")
        void cancelChallenge_NotCreator() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.cancelChallenge(partnerId, 1L));
            assertEquals("只有创建者可以取消挑战", ex.getMessage());
        }

        @Test
        @DisplayName("取消挑战-已完成的挑战应抛异常")
        void cancelChallenge_NotInProgress() {
            // Given
            Challenge challenge = createChallenge(1L, 1);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.cancelChallenge(userId, 1L));
            assertEquals("挑战状态不允许取消", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("打卡")
    class CheckinTest {

        @Test
        @DisplayName("打卡-成功")
        void checkin_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);
            when(checkinRecordMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(checkinRecordMapper.insert(any(CheckinRecord.class))).thenReturn(1);

            CheckinRecord existingRecord = new CheckinRecord();
            existingRecord.setCheckinDate(LocalDate.now());
            when(checkinRecordMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(existingRecord));

            // When
            CheckinReq req = new CheckinReq();
            req.setChallengeId(1L);
            req.setContent("今天早起啦！");
            CheckinRecordDTO result = challengeService.checkin(userId, req);

            // Then
            assertNotNull(result);
            verify(checkinRecordMapper).insert(any(CheckinRecord.class));
        }

        @Test
        @DisplayName("打卡-挑战不存在应抛异常")
        void checkin_ChallengeNotFound() {
            // Given
            when(challengeMapper.selectById(999L)).thenReturn(null);

            // When & Then
            CheckinReq req = new CheckinReq();
            req.setChallengeId(999L);
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.checkin(userId, req));
            assertEquals("挑战不存在", ex.getMessage());
        }

        @Test
        @DisplayName("打卡-非参与者应抛异常")
        void checkin_NotParticipant() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then
            CheckinReq req = new CheckinReq();
            req.setChallengeId(1L);
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.checkin(999L, req));
            assertEquals("您不是该挑战的参与者", ex.getMessage());
        }

        @Test
        @DisplayName("打卡-挑战已结束应抛异常")
        void checkin_ChallengeEnded() {
            // Given
            Challenge challenge = createChallenge(1L, 1); // 已完成
            when(challengeMapper.selectById(1L)).thenReturn(challenge);

            // When & Then
            CheckinReq req = new CheckinReq();
            req.setChallengeId(1L);
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.checkin(userId, req));
            assertEquals("挑战已结束", ex.getMessage());
        }

        @Test
        @DisplayName("打卡-今日已打卡应抛异常")
        void checkin_AlreadyCheckedToday() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);
            when(checkinRecordMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);

            // When & Then
            CheckinReq req = new CheckinReq();
            req.setChallengeId(1L);
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.checkin(userId, req));
            assertEquals("今日已打卡", ex.getMessage());
        }

        @Test
        @DisplayName("打卡-达到目标天数应自动完成挑战")
        void checkin_AutoComplete() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            challenge.setTargetDays(1); // 只需要1天
            challenge.setCurrentDays(0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);
            when(checkinRecordMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(checkinRecordMapper.insert(any(CheckinRecord.class))).thenReturn(1);

            // 模拟打卡后uniqueDates.size() == 1 >= targetDays == 1
            CheckinRecord existingRecord = new CheckinRecord();
            existingRecord.setCheckinDate(LocalDate.now());
            when(checkinRecordMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(existingRecord));

            // When
            CheckinReq req = new CheckinReq();
            req.setChallengeId(1L);
            challengeService.checkin(userId, req);

            // Then
            verify(challengeMapper).updateById(argThat(c -> c.getStatus() == 1));
        }
    }

    @Nested
    @DisplayName("获取挑战详情")
    class GetChallengeDetailTest {

        @Test
        @DisplayName("获取详情-成功")
        void getChallengeDetail_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);
            mockGetCoupleByUserId();
            when(userMapper.selectBatchIds(anyCollection()))
                    .thenReturn(Arrays.asList(creator, partner));
            when(checkinRecordMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(checkinRecordMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            ChallengeDTO result = challengeService.getChallengeDetail(userId, 1L);

            // Then
            assertNotNull(result);
            assertEquals(1L, result.getId());
            assertFalse(result.getTodayChecked());
        }

        @Test
        @DisplayName("获取详情-无权查看应抛异常")
        void getChallengeDetail_NoPermission() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            challenge.setCoupleId(999L); // 不同情侣
            when(challengeMapper.selectById(1L)).thenReturn(challenge);
            mockGetCoupleByUserId();

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.getChallengeDetail(userId, 1L));
            assertEquals("无权查看该挑战", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("获取挑战列表")
    class GetChallengeListTest {

        @Test
        @DisplayName("获取列表-成功")
        void getChallengeList_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            mockGetCoupleByUserId();
            when(challengeMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(challenge));
            when(userMapper.selectBatchIds(anyCollection()))
                    .thenReturn(Arrays.asList(creator, partner));

            // When
            List<ChallengeDTO> result = challengeService.getChallengeList(userId, null);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
        }

        @Test
        @DisplayName("获取列表-按状态筛选")
        void getChallengeList_WithStatus() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            mockGetCoupleByUserId();
            when(challengeMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(challenge));
            when(userMapper.selectBatchIds(anyCollection()))
                    .thenReturn(Arrays.asList(creator, partner));

            // When
            List<ChallengeDTO> result = challengeService.getChallengeList(userId, 0);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
        }
    }

    @Nested
    @DisplayName("获取待接受挑战")
    class GetPendingChallengesTest {

        @Test
        @DisplayName("获取待接受挑战-成功")
        void getPendingChallenges_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            mockGetCoupleByUserId();
            when(challengeMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(challenge));
            when(userMapper.selectBatchIds(anyCollection()))
                    .thenReturn(Arrays.asList(creator, partner));

            // When
            List<ChallengeDTO> result = challengeService.getPendingChallenges(userId);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
        }
    }

    @Nested
    @DisplayName("获取打卡记录")
    class GetCheckinRecordsTest {

        @Test
        @DisplayName("获取打卡记录-成功")
        void getCheckinRecords_Success() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);
            mockGetCoupleByUserId();

            Page<CheckinRecord> page = new Page<>(1, 10);
            when(checkinRecordMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
                    .thenReturn(page);

            // When
            Page<CheckinRecordDTO> result = challengeService.getCheckinRecords(userId, 1L, 1, 10);

            // Then
            assertNotNull(result);
        }

        @Test
        @DisplayName("获取打卡记录-无权查看应抛异常")
        void getCheckinRecords_NoPermission() {
            // Given
            Challenge challenge = createChallenge(1L, 0);
            challenge.setCoupleId(999L);
            when(challengeMapper.selectById(1L)).thenReturn(challenge);
            mockGetCoupleByUserId();

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> challengeService.getCheckinRecords(userId, 1L, 1, 10));
            assertEquals("无权查看该挑战的打卡记录", ex.getMessage());
        }
    }
}
