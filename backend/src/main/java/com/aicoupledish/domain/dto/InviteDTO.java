package com.aicoupledish.domain.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 邀请DTO
 */
@Data
public class InviteDTO {

    /**
     * 邀请码
     */
    private String inviteCode;

    /**
     * 邀请人数
     */
    private Integer inviteCount;

    /**
     * 奖励金额
     */
    private BigDecimal rewardAmount;

    /**
     * 邀请链接
     */
    private String inviteLink;

    /**
     * 邀请二维码
     */
    private String inviteQrCode;

    /**
     * 邀请规则说明
     */
    private List<InviteRule> rules;

    /**
     * 邀请记录列表
     */
    private List<InviteRecord> records;

    /**
     * 邀请统计
     */
    private InviteStats stats;

    /**
     * 邀请规则
     */
    @Data
    public static class InviteRule {
        private Integer level;
        private String title;
        private String description;
        private BigDecimal rewardAmount;
        private Integer requiredCount;
    }

    /**
     * 邀请记录
     */
    @Data
    public static class InviteRecord {
        private Long id;
        private Long inviteeId;
        private String inviteeName;
        private String inviteeAvatar;
        private LocalDateTime registerTime;
        private Integer status;
        private String statusName;
        private BigDecimal rewardAmount;
        private LocalDateTime rewardTime;
    }

    /**
     * 邀请统计
     */
    @Data
    public static class InviteStats {
        /**
         * 总邀请人数
         */
        private Integer totalCount;

        /**
         * 已绑定情侣人数
         */
        private Integer bindCoupleCount;

        /**
         * 待发放奖励数
         */
        private Integer pendingRewardCount;

        /**
         * 已发放奖励数
         */
        private Integer rewardedCount;

        /**
         * 总奖励金额
         */
        private BigDecimal totalRewardAmount;
    }

    /**
     * 使用邀请码请求
     */
    @Data
    public static class UseInviteCodeReq {
        private String inviteCode;
    }
}
