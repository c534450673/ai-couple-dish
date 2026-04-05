package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 心动时刻DTO
 */
@Data
public class HeartMomentDTO {

    private Long id;

    /**
     * 时刻类型：text/voice/photo
     */
    private String momentType;

    /**
     * 内容
     */
    private String content;

    /**
     * 媒体URL
     */
    private String mediaUrl;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 创建者信息
     */
    private CreatorInfo creator;

    /**
     * 时间描述（如：3分钟前、昨天、3天前）
     */
    private String timeDesc;

    @Data
    public static class CreatorInfo {
        private Long id;
        private String nickName;
        private String avatarUrl;
    }
}
