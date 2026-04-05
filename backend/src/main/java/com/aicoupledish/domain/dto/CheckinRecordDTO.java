package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 打卡记录DTO
 */
@Data
public class CheckinRecordDTO {

    /**
     * 记录ID
     */
    private Long id;

    /**
     * 挑战ID
     */
    private Long challengeId;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 用户名称
     */
    private String userName;

    /**
     * 用户头像
     */
    private String userAvatar;

    /**
     * 打卡日期
     */
    private LocalDate checkinDate;

    /**
     * 打卡内容
     */
    private String content;

    /**
     * 打卡图片
     */
    private String imageUrl;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;
}
