package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 情侣段位DTO
 */
@Data
public class CoupleRankDTO {

    private Long id;

    /**
     * 当前段位
     */
    private String currentRank;

    /**
     * 段位名称
     */
    private String rankName;

    /**
     * 段位图标
     */
    private String rankIcon;

    /**
     * 段位分数
     */
    private Integer rankScore;

    /**
     * 当前段位最低分数
     */
    private Integer currentRankMinScore;

    /**
     * 下一段位所需分数
     */
    private Integer nextRankScore;

    /**
     * 升级进度百分比
     */
    private Integer progressPercent;

    /**
     * 连续互动天数
     */
    private Integer consecutiveInteractionDays;

    /**
     * 恋爱温度
     */
    private Integer temperatureScore;

    /**
     * 温度等级
     */
    private String temperatureLevel;

    /**
     * 最近晋升时间
     */
    private LocalDateTime promotionDate;

    /**
     * 降级预警
     */
    private Boolean demotionWarning;

    /**
     * 可用段位列表
     */
    private List<RankInfo> rankList;

    /**
     * 段位信息
     */
    @Data
    public static class RankInfo {
        private String rank;
        private String name;
        private String icon;
        private Integer minScore;
        private Integer maxScore;
        private String description;
        private Boolean unlocked;
    }

    /**
     * 段位奖励
     */
    @Data
    public static class RankReward {
        private String rank;
        private String rewardType;
        private String rewardContent;
        private Boolean claimed;
    }
}
