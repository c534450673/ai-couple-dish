package com.aicoupledish.domain.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 邀请记录DTO
 */
@Data
public class ReferralDTO {

    private Long id;

    /**
     * 被邀请人ID
     */
    private Long inviteeId;

    /**
     * 被邀请人昵称
     */
    private String inviteeName;

    /**
     * 被邀请人头像
     */
    private String inviteeAvatar;

    /**
     * 邀请码
     */
    private String inviteCode;

    /**
     * 注册时间
     */
    private LocalDateTime registerTime;

    /**
     * 是否绑定情侣
     */
    private Boolean hasBoundCouple;

    /**
     * 绑定情侣时间
     */
    private LocalDateTime bindCoupleTime;

    /**
     * 奖励状态: 0-待发放 1-已发放
     */
    private Integer rewardStatus;

    /**
     * 奖励状态名称
     */
    private String rewardStatusName;

    /**
     * 奖励金额
     */
    private BigDecimal rewardAmount;

    /**
     * 奖励发放时间
     */
    private LocalDateTime rewardTime;
}
