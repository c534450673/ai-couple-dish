package com.aicoupledish.domain.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * 邀请统计DTO
 */
@Data
public class InviteStatsDTO {

    /**
     * 总邀请人数
     */
    private Integer totalInvites;

    /**
     * 已绑定情侣人数
     */
    private Integer boundCoupleCount;

    /**
     * 待绑定人数
     */
    private Integer pendingBindCount;

    /**
     * 总奖励金额
     */
    private BigDecimal totalRewardAmount;

    /**
     * 已发放奖励金额
     */
    private BigDecimal claimedRewardAmount;

    /**
     * 待发放奖励金额
     */
    private BigDecimal pendingRewardAmount;

    /**
     * 本周新增邀请
     */
    private Integer weeklyNewInvites;

    /**
     * 本月新增邀请
     */
    private Integer monthlyNewInvites;

    /**
     * 邀请排行列表
     */
    private List<InviteRankItem> rankList;

    /**
     * 邀请排行项
     */
    @Data
    public static class InviteRankItem {
        /**
         * 排名
         */
        private Integer rank;

        /**
         * 用户ID
         */
        private Long userId;

        /**
         * 用户昵称
         */
        private String userName;

        /**
         * 用户头像
         */
        private String userAvatar;

        /**
         * 邀请人数
         */
        private Integer inviteCount;

        /**
         * 奖励金额
         */
        private BigDecimal rewardAmount;
    }
}
