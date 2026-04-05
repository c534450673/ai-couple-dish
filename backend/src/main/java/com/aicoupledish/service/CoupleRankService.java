package com.aicoupledish.service;

import com.aicoupledish.domain.dto.CoupleRankDTO;

import java.util.List;

/**
 * 情侣段位服务接口
 */
public interface CoupleRankService {

    /**
     * 获取段位信息
     */
    CoupleRankDTO getRankInfo(Long userId);

    /**
     * 增加段位分数
     */
    void addRankScore(Long coupleId, Integer score, String source);

    /**
     * 减少段位分数
     */
    void reduceRankScore(Long coupleId, Integer score, String reason);

    /**
     * 更新连续互动天数
     */
    void updateConsecutiveDays(Long coupleId);

    /**
     * 更新恋爱温度
     */
    void updateTemperature(Long coupleId);

    /**
     * 获取段位排行
     */
    List<CoupleRankDTO> getRankList(Integer limit);

    /**
     * 获取段位奖励列表
     */
    List<CoupleRankDTO.RankReward> getRankRewards(Long userId);

    /**
     * 领取段位奖励
     */
    void claimRankReward(Long userId, String rank);
}
