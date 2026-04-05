package com.aicoupledish.domain.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 邀请码DTO
 */
@Data
public class InviteCodeDTO {

    private Long id;

    /**
     * 邀请码
     */
    private String inviteCode;

    /**
     * 邀请人数
     */
    private Integer inviteCount;

    /**
     * 已绑定情侣的邀请人数
     */
    private Integer boundCount;

    /**
     * 奖励金额
     */
    private BigDecimal rewardAmount;

    /**
     * 待发放奖励金额
     */
    private BigDecimal pendingRewardAmount;

    /**
     * 邀请链接
     */
    private String inviteLink;

    /**
     * 邀请二维码URL
     */
    private String qrcodeUrl;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;
}
