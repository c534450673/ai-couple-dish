package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.InviteCodeDTO;
import com.aicoupledish.domain.dto.InviteStatsDTO;
import com.aicoupledish.domain.dto.ReferralDTO;
import com.aicoupledish.service.impl.InviteServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 邀请服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("邀请服务测试")
class InviteServiceTest {

    @Mock
    private UserInviteCodeMapper userInviteCodeMapper;

    @Mock
    private UserReferralMapper userReferralMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @InjectMocks
    private InviteServiceImpl inviteService;

    private Long userId;
    private Long inviteeId;
    private User user;
    private User invitee;
    private UserInviteCode inviteCode;
    private Couple couple;

    @BeforeEach
    void setUp() {
        userId = 1L;
        inviteeId = 2L;

        user = new User();
        user.setId(userId);
        user.setNickName("小明");
        user.setAvatarUrl("/avatar/1.png");

        invitee = new User();
        invitee.setId(inviteeId);
        invitee.setNickName("小红");
        invitee.setAvatarUrl("/avatar/2.png");
        invitee.setCoupleId(100L);

        inviteCode = new UserInviteCode();
        inviteCode.setId(1L);
        inviteCode.setUserId(userId);
        inviteCode.setInviteCode("ABC123");
        inviteCode.setInviteCount(3);
        inviteCode.setRewardAmount(BigDecimal.valueOf(15.00));

        couple = new Couple();
        couple.setId(100L);
        couple.setUser1Id(inviteeId);
        couple.setUser2Id(3L);
        couple.setStatus(1);

        // Set @Value fields via reflection
        ReflectionTestUtils.setField(inviteService, "inviteLinkPrefix", "https://aicoupledish.com/invite/");
        ReflectionTestUtils.setField(inviteService, "registerReward", new BigDecimal("5.00"));
        ReflectionTestUtils.setField(inviteService, "bindCoupleReward", new BigDecimal("10.00"));
    }

    @Nested
    @DisplayName("获取或创建邀请码")
    class GetOrCreateInviteCode {

        @Test
        @DisplayName("获取或创建邀请码-已存在邀请码")
        void getOrCreateInviteCode_existing() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(userInviteCodeMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(inviteCode);
            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);
            when(userReferralMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Collections.emptyList());

            // When
            InviteCodeDTO result = inviteService.getOrCreateInviteCode(userId);

            // Then
            assertNotNull(result);
            assertEquals("ABC123", result.getInviteCode());
            assertEquals(3, result.getInviteCount());
            assertTrue(result.getInviteLink().contains("ABC123"));
        }

        @Test
        @DisplayName("获取或创建邀请码-不存在时自动创建")
        void getOrCreateInviteCode_createNew() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(userInviteCodeMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(userInviteCodeMapper.insert(any(UserInviteCode.class))).thenReturn(1);
            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(userReferralMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Collections.emptyList());

            // When
            InviteCodeDTO result = inviteService.getOrCreateInviteCode(userId);

            // Then
            assertNotNull(result);
            verify(userInviteCodeMapper).insert(argThat(code ->
                    code.getUserId().equals(userId) &&
                    code.getInviteCode() != null &&
                    code.getInviteCount() == 0
            ));
        }

        @Test
        @DisplayName("获取或创建邀请码-用户不存在应抛异常")
        void getOrCreateInviteCode_userNotFound_throw() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> inviteService.getOrCreateInviteCode(userId));
            assertEquals(BusinessException.USER_NOT_FOUND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("使用邀请码")
    class UseInviteCode {

        @Test
        @DisplayName("使用邀请码-成功")
        void useInviteCode_success() {
            // Given
            when(userMapper.selectById(inviteeId)).thenReturn(invitee);
            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(userInviteCodeMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(inviteCode);
            when(userReferralMapper.insert(any(UserReferral.class))).thenReturn(1);

            // When
            inviteService.useInviteCode(inviteeId, "ABC123");

            // Then
            verify(userReferralMapper).insert(argThat(referral ->
                    referral.getInviterId().equals(userId) &&
                    referral.getInviteeId().equals(inviteeId) &&
                    referral.getRewardAmount().compareTo(new BigDecimal("5.00")) == 0
            ));
            verify(userInviteCodeMapper).update(any(), any(LambdaUpdateWrapper.class));
        }

        @Test
        @DisplayName("使用邀请码-空邀请码静默返回")
        void useInviteCode_nullCode_return() {
            // When
            inviteService.useInviteCode(inviteeId, null);

            // Then
            verify(userReferralMapper, never()).insert(any());
        }

        @Test
        @DisplayName("使用邀请码-空字符串邀请码静默返回")
        void useInviteCode_emptyCode_return() {
            // When
            inviteService.useInviteCode(inviteeId, "  ");

            // Then
            verify(userReferralMapper, never()).insert(any());
        }

        @Test
        @DisplayName("使用邀请码-已使用过邀请码静默返回")
        void useInviteCode_alreadyUsed_return() {
            // Given
            when(userMapper.selectById(inviteeId)).thenReturn(invitee);
            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);

            // When
            inviteService.useInviteCode(inviteeId, "ABC123");

            // Then
            verify(userReferralMapper, never()).insert(any());
        }

        @Test
        @DisplayName("使用邀请码-邀请码不存在静默返回")
        void useInviteCode_codeNotFound_return() {
            // Given
            when(userMapper.selectById(inviteeId)).thenReturn(invitee);
            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(userInviteCodeMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            inviteService.useInviteCode(inviteeId, "NOTEXIST");

            // Then
            verify(userReferralMapper, never()).insert(any());
        }

        @Test
        @DisplayName("使用邀请码-不能使用自己的邀请码静默返回")
        void useInviteCode_selfCode_return() {
            // Given
            inviteCode.setUserId(userId); // same user
            when(userMapper.selectById(userId)).thenReturn(user);
            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
            when(userInviteCodeMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(inviteCode);

            // When
            inviteService.useInviteCode(userId, "ABC123");

            // Then
            verify(userReferralMapper, never()).insert(any());
        }

        @Test
        @DisplayName("使用邀请码-用户不存在应抛异常")
        void useInviteCode_userNotFound_throw() {
            // Given
            when(userMapper.selectById(inviteeId)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> inviteService.useInviteCode(inviteeId, "ABC123"));
            assertEquals(BusinessException.USER_NOT_FOUND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("获取邀请统计")
    class GetInviteStats {

        @Test
        @DisplayName("获取邀请统计-成功")
        void getInviteStats_success() {
            // Given
            UserReferral referral = new UserReferral();
            referral.setId(1L);
            referral.setInviterId(userId);
            referral.setInviteeId(inviteeId);
            referral.setRewardStatus(0);
            referral.setRewardAmount(new BigDecimal("5.00"));

            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class)))
                    .thenReturn(3L)   // total
                    .thenReturn(1L)   // bound couple
                    .thenReturn(0L)   // weekly new
                    .thenReturn(0L);  // monthly
            when(userReferralMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(referral));

            // When
            InviteStatsDTO result = inviteService.getInviteStats(userId);

            // Then
            assertNotNull(result);
            assertEquals(3, result.getTotalInvites());
            assertEquals(1, result.getBoundCoupleCount());
            assertEquals(2, result.getPendingBindCount());
        }

        @Test
        @DisplayName("获取邀请统计-无邀请记录")
        void getInviteStats_noReferrals() {
            // Given
            when(userReferralMapper.selectCount(any(LambdaQueryWrapper.class)))
                    .thenReturn(0L);
            when(userReferralMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            InviteStatsDTO result = inviteService.getInviteStats(userId);

            // Then
            assertNotNull(result);
            assertEquals(0, result.getTotalInvites());
            assertEquals(BigDecimal.ZERO, result.getTotalRewardAmount());
        }
    }

    @Nested
    @DisplayName("获取邀请列表")
    class GetReferralList {

        @Test
        @DisplayName("获取邀请列表-成功")
        void getReferralList_success() {
            // Given
            UserReferral referral = new UserReferral();
            referral.setId(1L);
            referral.setInviterId(userId);
            referral.setInviteeId(inviteeId);
            referral.setInviteCode("ABC123");
            referral.setRewardStatus(0);
            referral.setRewardAmount(new BigDecimal("5.00"));
            referral.setRegisterTime(LocalDateTime.now());

            when(userReferralMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(referral));
            when(userMapper.selectById(inviteeId)).thenReturn(invitee);

            // When
            List<ReferralDTO> result = inviteService.getReferralList(userId, 10);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals("小红", result.get(0).getInviteeName());
            assertEquals("待发放", result.get(0).getRewardStatusName());
            assertFalse(result.get(0).getHasBoundCouple());
        }

        @Test
        @DisplayName("获取邀请列表-已绑定情侣")
        void getReferralList_boundCouple() {
            // Given
            UserReferral referral = new UserReferral();
            referral.setId(1L);
            referral.setInviterId(userId);
            referral.setInviteeId(inviteeId);
            referral.setInviteCode("ABC123");
            referral.setRewardStatus(1);
            referral.setRewardAmount(new BigDecimal("15.00"));
            referral.setBindCoupleTime(LocalDateTime.now());
            referral.setRegisterTime(LocalDateTime.now());

            when(userReferralMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(referral));
            when(userMapper.selectById(inviteeId)).thenReturn(invitee);

            // When
            List<ReferralDTO> result = inviteService.getReferralList(userId, 10);

            // Then
            assertTrue(result.get(0).getHasBoundCouple());
            assertEquals("已发放", result.get(0).getRewardStatusName());
        }
    }

    @Nested
    @DisplayName("处理绑定情侣奖励")
    class ProcessBindCoupleReward {

        @Test
        @DisplayName("处理绑定情侣奖励-成功")
        void processBindCoupleReward_success() {
            // Given
            UserReferral referral = new UserReferral();
            referral.setId(1L);
            referral.setInviterId(userId);
            referral.setInviteeId(inviteeId);
            referral.setRewardAmount(new BigDecimal("5.00"));

            when(userReferralMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(referral);
            when(userMapper.selectById(inviteeId)).thenReturn(invitee);
            when(coupleMapper.selectById(100L)).thenReturn(couple);
            when(userReferralMapper.updateById(any(UserReferral.class))).thenReturn(1);

            // When
            inviteService.processBindCoupleReward(inviteeId);

            // Then
            verify(userReferralMapper).updateById(argThat(r ->
                    r.getBindCoupleTime() != null &&
                    r.getRewardAmount().compareTo(new BigDecimal("15.00")) == 0
            ));
        }

        @Test
        @DisplayName("处理绑定情侣奖励-无邀请关系静默返回")
        void processBindCoupleReward_noReferral_return() {
            // Given
            when(userReferralMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            inviteService.processBindCoupleReward(inviteeId);

            // Then
            verify(userReferralMapper, never()).updateById(any());
        }

        @Test
        @DisplayName("处理绑定情侣奖励-用户未绑定情侣静默返回")
        void processBindCoupleReward_notBound_return() {
            // Given
            invitee.setCoupleId(null);
            UserReferral referral = new UserReferral();
            referral.setId(1L);
            referral.setInviteeId(inviteeId);

            when(userReferralMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(referral);
            when(userMapper.selectById(inviteeId)).thenReturn(invitee);

            // When
            inviteService.processBindCoupleReward(inviteeId);

            // Then
            verify(userReferralMapper, never()).updateById(any());
        }

        @Test
        @DisplayName("处理绑定情侣奖励-用户不存在静默返回")
        void processBindCoupleReward_userNotFound_return() {
            // Given
            UserReferral referral = new UserReferral();
            referral.setId(1L);
            referral.setInviteeId(inviteeId);

            when(userReferralMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(referral);
            when(userMapper.selectById(inviteeId)).thenReturn(null);

            // When
            inviteService.processBindCoupleReward(inviteeId);

            // Then
            verify(userReferralMapper, never()).updateById(any());
        }
    }

    @Nested
    @DisplayName("获取邀请排行榜")
    class GetInviteRankList {

        @Test
        @DisplayName("获取邀请排行榜-成功")
        void getInviteRankList_success() {
            // Given
            UserInviteCode topCode = new UserInviteCode();
            topCode.setId(1L);
            topCode.setUserId(userId);
            topCode.setInviteCount(10);
            topCode.setRewardAmount(BigDecimal.valueOf(50));

            when(userInviteCodeMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(topCode));
            when(userMapper.selectById(userId)).thenReturn(user);

            // When
            List<InviteStatsDTO.InviteRankItem> result = inviteService.getInviteRankList(10);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals(1, result.get(0).getRank());
            assertEquals("小明", result.get(0).getUserName());
            assertEquals(10, result.get(0).getInviteCount());
        }

        @Test
        @DisplayName("获取邀请排行榜-空列表")
        void getInviteRankList_empty() {
            // Given
            when(userInviteCodeMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            List<InviteStatsDTO.InviteRankItem> result = inviteService.getInviteRankList(10);

            // Then
            assertNotNull(result);
            assertTrue(result.isEmpty());
        }
    }

    @Nested
    @DisplayName("验证邀请码")
    class ValidateInviteCode {

        @Test
        @DisplayName("验证邀请码-有效")
        void validateInviteCode_valid() {
            // Given
            when(userInviteCodeMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);

            // When
            boolean result = inviteService.validateInviteCode("ABC123");

            // Then
            assertTrue(result);
        }

        @Test
        @DisplayName("验证邀请码-无效")
        void validateInviteCode_invalid() {
            // Given
            when(userInviteCodeMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);

            // When
            boolean result = inviteService.validateInviteCode("NOTEXIST");

            // Then
            assertFalse(result);
        }

        @Test
        @DisplayName("验证邀请码-null返回false")
        void validateInviteCode_null_false() {
            // When
            boolean result = inviteService.validateInviteCode(null);

            // Then
            assertFalse(result);
        }

        @Test
        @DisplayName("验证邀请码-空字符串返回false")
        void validateInviteCode_empty_false() {
            // When
            boolean result = inviteService.validateInviteCode("  ");

            // Then
            assertFalse(result);
        }
    }

    @Nested
    @DisplayName("获取邀请码信息")
    class GetInviteCodeInfo {

        @Test
        @DisplayName("获取邀请码信息-成功")
        void getInviteCodeInfo_success() {
            // Given
            when(userInviteCodeMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(inviteCode);

            // When
            InviteCodeDTO result = inviteService.getInviteCodeInfo("ABC123");

            // Then
            assertNotNull(result);
            assertEquals("ABC123", result.getInviteCode());
            assertEquals(3, result.getInviteCount());
        }

        @Test
        @DisplayName("获取邀请码信息-不存在返回null")
        void getInviteCodeInfo_notFound_null() {
            // Given
            when(userInviteCodeMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            InviteCodeDTO result = inviteService.getInviteCodeInfo("NOTEXIST");

            // Then
            assertNull(result);
        }
    }
}
