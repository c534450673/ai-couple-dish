package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.CoupleRankMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.CoupleRank;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.CoupleRankDTO;
import com.aicoupledish.service.CoupleRankService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 情侣段位服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CoupleRankServiceImpl implements CoupleRankService {

    private final CoupleRankMapper coupleRankMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    /**
     * 段位配置
     */
    private static final List<RankConfig> RANK_CONFIGS = Arrays.asList(
        new RankConfig("bronze", "青铜", "🥉", 0, 100, "初识阶段"),
        new RankConfig("silver", "白银", "🥈", 100, 300, "相识阶段"),
        new RankConfig("gold", "黄金", "🥇", 300, 600, "相知阶段"),
        new RankConfig("platinum", "铂金", "💎", 600, 1000, "相恋阶段"),
        new RankConfig("diamond", "钻石", "💍", 1000, 1500, "相爱阶段"),
        new RankConfig("king", "王者", "👑", 1500, Integer.MAX_VALUE, "相伴一生")
    );

    @Override
    public CoupleRankDTO getRankInfo(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleRank rank = getOrCreateRank(user.getCoupleId());
        return buildDTO(rank);
    }

    @Override
    @Transactional
    public void addRankScore(Long coupleId, Integer score, String source) {
        CoupleRank rank = getOrCreateRank(coupleId);

        // 使用原子更新避免竞态条件
        coupleRankMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<CoupleRank>()
                .eq(CoupleRank::getId, rank.getId())
                .setSql("rank_score = rank_score + " + score)
                .set(CoupleRank::getDemotionWarning, 0));

        // 重新查询更新后的数据
        rank = coupleRankMapper.selectById(rank.getId());

        // 检查是否升级
        String newRank = calculateRank(rank.getRankScore());
        if (!newRank.equals(rank.getCurrentRank())) {
            String oldRank = rank.getCurrentRank();
            rank.setCurrentRank(newRank);
            rank.setPromotionDate(LocalDateTime.now());
            coupleRankMapper.updateById(rank);
            log.info("情侣段位升级: coupleId={}, oldRank={}, newRank={}", coupleId, oldRank, newRank);
            // TODO: 发送升级通知和奖励
        }

        log.info("增加段位分数: coupleId={}, score={}, source={}", coupleId, score, source);
    }

    @Override
    @Transactional
    public void reduceRankScore(Long coupleId, Integer score, String reason) {
        CoupleRank rank = getOrCreateRank(coupleId);

        // 使用原子更新避免竞态条件，确保分数不为负
        coupleRankMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<CoupleRank>()
                .eq(CoupleRank::getId, rank.getId())
                .setSql("rank_score = GREATEST(0, rank_score - " + score + ")"));

        // 重新查询更新后的数据
        rank = coupleRankMapper.selectById(rank.getId());

        // 检查是否降级
        String newRank = calculateRank(rank.getRankScore());
        if (!newRank.equals(rank.getCurrentRank())) {
            String oldRank = rank.getCurrentRank();
            rank.setCurrentRank(newRank);
            rank.setDemotionWarning(1);
            coupleRankMapper.updateById(rank);
            log.info("情侣段位降级: coupleId={}, oldRank={}, newRank={}", coupleId, oldRank, newRank);
        }

        log.info("减少段位分数: coupleId={}, score={}, reason={}", coupleId, score, reason);
    }

    @Override
    @Transactional
    public void updateConsecutiveDays(Long coupleId) {
        CoupleRank rank = getOrCreateRank(coupleId);

        // 使用原子更新避免竞态条件
        coupleRankMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<CoupleRank>()
                .eq(CoupleRank::getId, rank.getId())
                .setSql("consecutive_interaction_days = consecutive_interaction_days + 1"));
    }

    @Override
    @Transactional
    public void updateTemperature(Long coupleId) {
        CoupleRank rank = getOrCreateRank(coupleId);

        // 温度范围: 0-100
        int temperature = rank.getTemperatureScore();

        // 连续互动增加温度，不互动减少温度
        // 这里简化处理，实际应该根据互动记录计算
        if (rank.getConsecutiveInteractionDays() > 0) {
            temperature = Math.min(100, temperature + 1);
        } else {
            temperature = Math.max(0, temperature - 1);
        }

        rank.setTemperatureScore(temperature);
        coupleRankMapper.updateById(rank);
    }

    @Override
    public List<CoupleRankDTO> getRankList(Integer limit) {
        List<CoupleRank> ranks = coupleRankMapper.selectList(
            new LambdaQueryWrapper<CoupleRank>()
                    .orderByDesc(CoupleRank::getRankScore)
                    .last("LIMIT " + (limit != null ? limit : 100))
        );

        return ranks.stream().map(this::buildDTO).collect(Collectors.toList());
    }

    @Override
    public List<CoupleRankDTO.RankReward> getRankRewards(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleRank rank = getOrCreateRank(user.getCoupleId());
        List<CoupleRankDTO.RankReward> rewards = new ArrayList<>();

        for (RankConfig config : RANK_CONFIGS) {
            CoupleRankDTO.RankReward reward = new CoupleRankDTO.RankReward();
            reward.setRank(config.rank);
            reward.setRewardType("skin");
            reward.setRewardContent(config.name + "专属头像框");
            reward.setClaimed(hasReachedRank(rank.getRankScore(), config.rank));
            rewards.add(reward);
        }

        return rewards;
    }

    @Override
    @Transactional
    public void claimRankReward(Long userId, String rank) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleRank coupleRank = getOrCreateRank(user.getCoupleId());

        if (!hasReachedRank(coupleRank.getRankScore(), rank)) {
            throw new IllegalArgumentException("尚未达到该段位");
        }

        // TODO: 实际发放奖励
        log.info("领取段位奖励: userId={}, rank={}", userId, rank);
    }

    /**
     * 获取或创建段位记录
     */
    private CoupleRank getOrCreateRank(Long coupleId) {
        CoupleRank rank = coupleRankMapper.selectOne(
            new LambdaQueryWrapper<CoupleRank>()
                    .eq(CoupleRank::getCoupleId, coupleId)
        );

        if (rank == null) {
            rank = new CoupleRank();
            rank.setCoupleId(coupleId);
            rank.setCurrentRank("bronze");
            rank.setRankScore(0);
            rank.setConsecutiveInteractionDays(0);
            rank.setTemperatureScore(60); // 默认60度
            rank.setDemotionWarning(0);
            coupleRankMapper.insert(rank);
            log.info("创建情侣段位: coupleId={}", coupleId);
        }

        return rank;
    }

    /**
     * 根据分数计算段位
     */
    private String calculateRank(Integer score) {
        for (RankConfig config : RANK_CONFIGS) {
            if (score < config.maxScore) {
                return config.rank;
            }
        }
        return "king";
    }

    /**
     * 检查是否达到指定段位
     */
    private boolean hasReachedRank(Integer score, String rank) {
        int rankIndex = -1;
        int currentRankIndex = -1;

        for (int i = 0; i < RANK_CONFIGS.size(); i++) {
            if (RANK_CONFIGS.get(i).rank.equals(rank)) {
                rankIndex = i;
            }
            if (score < RANK_CONFIGS.get(i).maxScore && currentRankIndex == -1) {
                currentRankIndex = i;
            }
        }

        return currentRankIndex >= rankIndex;
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private CoupleRankDTO buildDTO(CoupleRank rank) {
        CoupleRankDTO dto = new CoupleRankDTO();
        dto.setId(rank.getId());
        dto.setCurrentRank(rank.getCurrentRank());
        dto.setRankScore(rank.getRankScore());
        dto.setConsecutiveInteractionDays(rank.getConsecutiveInteractionDays());
        dto.setTemperatureScore(rank.getTemperatureScore());
        dto.setPromotionDate(rank.getPromotionDate());
        dto.setDemotionWarning(rank.getDemotionWarning() == 1);

        // 获取段位信息
        RankConfig currentConfig = null;
        RankConfig nextConfig = null;

        for (int i = 0; i < RANK_CONFIGS.size(); i++) {
            RankConfig config = RANK_CONFIGS.get(i);
            if (config.rank.equals(rank.getCurrentRank())) {
                currentConfig = config;
                if (i + 1 < RANK_CONFIGS.size()) {
                    nextConfig = RANK_CONFIGS.get(i + 1);
                }
                break;
            }
        }

        if (currentConfig != null) {
            dto.setRankName(currentConfig.name);
            dto.setRankIcon(currentConfig.icon);
            dto.setCurrentRankMinScore(currentConfig.minScore);
        }

        if (nextConfig != null) {
            dto.setNextRankScore(nextConfig.minScore);
            // 计算进度
            int currentMin = currentConfig != null ? currentConfig.minScore : 0;
            int nextMin = nextConfig.minScore;
            int progress = rank.getRankScore() - currentMin;
            int total = nextMin - currentMin;
            dto.setProgressPercent(total > 0 ? (progress * 100 / total) : 0);
        } else {
            dto.setNextRankScore(null);
            dto.setProgressPercent(100);
        }

        // 温度等级
        dto.setTemperatureLevel(getTemperatureLevel(rank.getTemperatureScore()));

        // 可用段位列表
        List<CoupleRankDTO.RankInfo> rankList = new ArrayList<>();
        for (RankConfig config : RANK_CONFIGS) {
            CoupleRankDTO.RankInfo info = new CoupleRankDTO.RankInfo();
            info.setRank(config.rank);
            info.setName(config.name);
            info.setIcon(config.icon);
            info.setMinScore(config.minScore);
            info.setMaxScore(config.maxScore);
            info.setDescription(config.description);
            info.setUnlocked(hasReachedRank(rank.getRankScore(), config.rank));
            rankList.add(info);
        }
        dto.setRankList(rankList);

        return dto;
    }

    private String getTemperatureLevel(Integer temperature) {
        if (temperature >= 90) return "火热";
        if (temperature >= 70) return "温暖";
        if (temperature >= 50) return "适中";
        if (temperature >= 30) return "微凉";
        return "冷淡";
    }

    /**
     * 段位配置
     */
    private static class RankConfig {
        String rank;
        String name;
        String icon;
        int minScore;
        int maxScore;
        String description;

        RankConfig(String rank, String name, String icon, int minScore, int maxScore, String description) {
            this.rank = rank;
            this.name = name;
            this.icon = icon;
            this.minScore = minScore;
            this.maxScore = maxScore;
            this.description = description;
        }
    }
}
