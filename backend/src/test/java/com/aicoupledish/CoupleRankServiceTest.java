package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.CoupleRankMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.CoupleRank;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.CoupleRankDTO;
import com.aicoupledish.service.impl.CoupleRankServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 情侣段位服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("情侣段位服务测试")
class CoupleRankServiceTest {

    @Mock
    private CoupleRankMapper coupleRankMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private CoupleRankServiceImpl coupleRankService;

    private Long userId;
    private Long coupleId;
    private User user;

    @BeforeEach
    void setUp() {
        userId = 1L;
        coupleId = 100L;

        user = new User();
        user.setId(userId);
        user.setNickName("小明");
        user.setCoupleId(coupleId);
    }

    private CoupleRank createRank(Long id, String currentRank, int score) {
        CoupleRank rank = new CoupleRank();
        rank.setId(id);
        rank.setCoupleId(coupleId);
        rank.setCurrentRank(currentRank);
        rank.setRankScore(score);
        rank.setConsecutiveInteractionDays(5);
        rank.setTemperatureScore(60);
        rank.setDemotionWarning(0);
        return rank;
    }

    @Nested
    @DisplayName("获取段位信息")
    class GetRankInfoTest {

        @Test
        @DisplayName("获取段位-成功")
        void getRankInfo_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            CoupleRank rank = createRank(1L, "bronze", 50);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            CoupleRankDTO result = coupleRankService.getRankInfo(userId);

            // Then
            assertNotNull(result);
            assertEquals("bronze", result.getCurrentRank());
            assertEquals(50, result.getRankScore());
            assertEquals("青铜", result.getRankName());
        }

        @Test
        @DisplayName("获取段位-未绑定情侣应抛异常")
        void getRankInfo_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> coupleRankService.getRankInfo(userId));
        }

        @Test
        @DisplayName("获取段位-自动创建新记录")
        void getRankInfo_AutoCreate() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(coupleRankMapper.insert(any(CoupleRank.class))).thenAnswer(invocation -> {
                CoupleRank r = invocation.getArgument(0);
                r.setId(1L);
                return 1;
            });

            // When
            CoupleRankDTO result = coupleRankService.getRankInfo(userId);

            // Then
            assertNotNull(result);
            verify(coupleRankMapper).insert(argThat(r ->
                    r.getCoupleId().equals(coupleId) &&
                    r.getCurrentRank().equals("bronze") &&
                    r.getRankScore() == 0
            ));
        }

        @Test
        @DisplayName("获取段位-用户不存在应抛异常")
        void getRankInfo_UserNotFound() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(null);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> coupleRankService.getRankInfo(userId));
        }
    }

    @Nested
    @DisplayName("增加段位分数")
    class AddRankScoreTest {

        @Test
        @DisplayName("增加分数-成功不升级")
        void addRankScore_Success_NoPromotion() {
            // Given
            CoupleRank rank = createRank(1L, "bronze", 50);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);
            when(coupleRankMapper.update(any(), any())).thenReturn(1);

            CoupleRank updatedRank = createRank(1L, "bronze", 80);
            when(coupleRankMapper.selectById(1L)).thenReturn(updatedRank);

            // When
            coupleRankService.addRankScore(coupleId, 30, "daily_task");

            // Then
            verify(coupleRankMapper).update(any(), any()); // atomic update
            verify(coupleRankMapper).selectById(1L); // re-query
            // No promotion, so no additional updateById for rank change
        }

        @Test
        @DisplayName("增加分数-升级成功")
        void addRankScore_Promotion() {
            // Given
            CoupleRank rank = createRank(1L, "bronze", 90);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);
            when(coupleRankMapper.update(any(), any())).thenReturn(1);

            CoupleRank updatedRank = createRank(1L, "bronze", 120);
            when(coupleRankMapper.selectById(1L)).thenReturn(updatedRank);

            // When
            coupleRankService.addRankScore(coupleId, 30, "daily_task");

            // Then
            verify(coupleRankMapper).updateById(argThat(r ->
                    r.getCurrentRank().equals("silver")
            ));
        }
    }

    @Nested
    @DisplayName("减少段位分数")
    class ReduceRankScoreTest {

        @Test
        @DisplayName("减少分数-成功不降级")
        void reduceRankScore_Success_NoDemotion() {
            // Given
            CoupleRank rank = createRank(1L, "silver", 150);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);
            when(coupleRankMapper.update(any(), any())).thenReturn(1);

            CoupleRank updatedRank = createRank(1L, "silver", 130);
            when(coupleRankMapper.selectById(1L)).thenReturn(updatedRank);

            // When
            coupleRankService.reduceRankScore(coupleId, 20, "inactive");

            // Then
            verify(coupleRankMapper).update(any(), any());
        }

        @Test
        @DisplayName("减少分数-降级成功")
        void reduceRankScore_Demotion() {
            // Given
            CoupleRank rank = createRank(1L, "silver", 110);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);
            when(coupleRankMapper.update(any(), any())).thenReturn(1);

            CoupleRank updatedRank = createRank(1L, "silver", 80);
            when(coupleRankMapper.selectById(1L)).thenReturn(updatedRank);

            // When
            coupleRankService.reduceRankScore(coupleId, 30, "inactive");

            // Then
            verify(coupleRankMapper).updateById(argThat(r ->
                    r.getCurrentRank().equals("bronze") &&
                    r.getDemotionWarning() == 1
            ));
        }
    }

    @Nested
    @DisplayName("更新连续互动天数")
    class UpdateConsecutiveDaysTest {

        @Test
        @DisplayName("更新连续天数-成功")
        void updateConsecutiveDays_Success() {
            // Given
            CoupleRank rank = createRank(1L, "bronze", 50);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);
            when(coupleRankMapper.update(any(), any())).thenReturn(1);

            // When
            coupleRankService.updateConsecutiveDays(coupleId);

            // Then
            verify(coupleRankMapper).update(any(), any());
        }
    }

    @Nested
    @DisplayName("更新温度")
    class UpdateTemperatureTest {

        @Test
        @DisplayName("更新温度-有连续互动增加温度")
        void updateTemperature_Increase() {
            // Given
            CoupleRank rank = createRank(1L, "bronze", 50);
            rank.setConsecutiveInteractionDays(3);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            coupleRankService.updateTemperature(coupleId);

            // Then
            verify(coupleRankMapper).updateById(argThat(r -> r.getTemperatureScore() == 61));
        }

        @Test
        @DisplayName("更新温度-无连续互动减少温度")
        void updateTemperature_Decrease() {
            // Given
            CoupleRank rank = createRank(1L, "bronze", 50);
            rank.setConsecutiveInteractionDays(0);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            coupleRankService.updateTemperature(coupleId);

            // Then
            verify(coupleRankMapper).updateById(argThat(r -> r.getTemperatureScore() == 59));
        }

        @Test
        @DisplayName("更新温度-最高不超过100")
        void updateTemperature_Max100() {
            // Given
            CoupleRank rank = createRank(1L, "bronze", 50);
            rank.setTemperatureScore(100);
            rank.setConsecutiveInteractionDays(5);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            coupleRankService.updateTemperature(coupleId);

            // Then
            verify(coupleRankMapper).updateById(argThat(r -> r.getTemperatureScore() == 100));
        }

        @Test
        @DisplayName("更新温度-最低不低于0")
        void updateTemperature_Min0() {
            // Given
            CoupleRank rank = createRank(1L, "bronze", 50);
            rank.setTemperatureScore(0);
            rank.setConsecutiveInteractionDays(0);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            coupleRankService.updateTemperature(coupleId);

            // Then
            verify(coupleRankMapper).updateById(argThat(r -> r.getTemperatureScore() == 0));
        }
    }

    @Nested
    @DisplayName("获取段位排行榜")
    class GetRankListTest {

        @Test
        @DisplayName("获取排行榜-成功")
        void getRankList_Success() {
            // Given
            CoupleRank rank1 = createRank(1L, "gold", 400);
            CoupleRank rank2 = createRank(2L, "silver", 200);
            when(coupleRankMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Arrays.asList(rank1, rank2));

            // When
            List<CoupleRankDTO> result = coupleRankService.getRankList(10);

            // Then
            assertNotNull(result);
            assertEquals(2, result.size());
        }

        @Test
        @DisplayName("获取排行榜-默认100条")
        void getRankList_DefaultLimit() {
            // Given
            when(coupleRankMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            coupleRankService.getRankList(null);

            // Then
            verify(coupleRankMapper).selectList(any(LambdaQueryWrapper.class));
        }
    }

    @Nested
    @DisplayName("获取段位奖励")
    class GetRankRewardsTest {

        @Test
        @DisplayName("获取段位奖励-成功")
        void getRankRewards_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            CoupleRank rank = createRank(1L, "silver", 150);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            List<CoupleRankDTO.RankReward> result = coupleRankService.getRankRewards(userId);

            // Then
            assertNotNull(result);
            assertEquals(6, result.size()); // 6个段位
            // Bronze and silver should be claimed
            assertTrue(result.get(0).getClaimed()); // bronze
            assertTrue(result.get(1).getClaimed()); // silver
            assertFalse(result.get(2).getClaimed()); // gold
        }

        @Test
        @DisplayName("获取段位奖励-未绑定情侣应抛异常")
        void getRankRewards_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> coupleRankService.getRankRewards(userId));
        }
    }

    @Nested
    @DisplayName("领取段位奖励")
    class ClaimRankRewardTest {

        @Test
        @DisplayName("领取奖励-成功")
        void claimRankReward_Success() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            CoupleRank rank = createRank(1L, "silver", 150);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When & Then - no exception
            assertDoesNotThrow(() -> coupleRankService.claimRankReward(userId, "silver"));
        }

        @Test
        @DisplayName("领取奖励-未达到段位应抛异常")
        void claimRankReward_NotReached() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            CoupleRank rank = createRank(1L, "bronze", 50);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When & Then
            assertThrows(IllegalArgumentException.class,
                    () -> coupleRankService.claimRankReward(userId, "gold"));
        }

        @Test
        @DisplayName("领取奖励-未绑定情侣应抛异常")
        void claimRankReward_NotBound() {
            // Given
            user.setCoupleId(null);
            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            assertThrows(BusinessException.class,
                    () -> coupleRankService.claimRankReward(userId, "bronze"));
        }
    }

    @Nested
    @DisplayName("段位进度计算")
    class RankProgressTest {

        @Test
        @DisplayName("青铜段位-正确进度百分比")
        void rankProgress_Bronze() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            CoupleRank rank = createRank(1L, "bronze", 50);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            CoupleRankDTO result = coupleRankService.getRankInfo(userId);

            // Then
            assertEquals(50, result.getProgressPercent()); // 50/100 * 100
        }

        @Test
        @DisplayName("王者段位-进度100%")
        void rankProgress_King() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            CoupleRank rank = createRank(1L, "king", 2000);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            CoupleRankDTO result = coupleRankService.getRankInfo(userId);

            // Then
            assertEquals(100, result.getProgressPercent());
        }

        @Test
        @DisplayName("温度等级-火热")
        void temperatureLevel_Hot() {
            // Given
            when(userMapper.selectById(userId)).thenReturn(user);
            CoupleRank rank = createRank(1L, "bronze", 50);
            rank.setTemperatureScore(95);
            when(coupleRankMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(rank);

            // When
            CoupleRankDTO result = coupleRankService.getRankInfo(userId);

            // Then
            assertEquals("火热", result.getTemperatureLevel());
        }
    }
}
