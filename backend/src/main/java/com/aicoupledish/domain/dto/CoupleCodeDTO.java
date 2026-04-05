package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 情侣码信息DTO
 */
@Data
public class CoupleCodeDTO {

    /**
     * 情侣码
     */
    private String coupleCode;

    /**
     * 生成时间（时间戳，毫秒）
     */
    private Long createTime;

    /**
     * 过期时间（时间戳，毫秒）
     */
    private Long expireTime;

    /**
     * 剩余有效时间（秒）
     */
    private Long remainingSeconds;

    /**
     * 剩余天数
     */
    private Long remainingDays;

    /**
     * 剩余小时
     */
    private Long remainingHours;

    /**
     * 剩余分钟
     */
    private Long remainingMinutes;

    /**
     * 是否即将过期（24小时内）
     */
    private Boolean expiringSoon;

    /**
     * 是否已过期
     */
    private Boolean expired;

    /**
     * 情侣码状态：valid-有效 expiring-即将过期 expired-已过期
     */
    private String status;

    /**
     * 生成者ID
     */
    private Long creatorId;

    /**
     * 生成者昵称
     */
    private String creatorNickName;

    /**
     * 生成者头像
     */
    private String creatorAvatar;
}
