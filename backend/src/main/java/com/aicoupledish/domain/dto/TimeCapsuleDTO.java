package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 时光胶囊DTO
 */
@Data
public class TimeCapsuleDTO {

    private Long id;

    /**
     * 胶囊类型：text/voice/video/photo
     */
    private String capsuleType;

    /**
     * 胶囊标题
     */
    private String title;

    /**
     * 胶囊内容
     */
    private String content;

    /**
     * 媒体URLs
     */
    private List<String> mediaUrls;

    /**
     * 解锁日期
     */
    private LocalDate unlockDate;

    /**
     * 状态：0-待解锁 1-已解锁
     */
    private Integer status;

    /**
     * 状态名称
     */
    private String statusName;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 解锁时间
     */
    private LocalDateTime unlockTime;

    /**
     * 创建者信息
     */
    private CreatorInfo creator;

    /**
     * 是否可以解锁
     */
    private Boolean canUnlock;

    /**
     * 距离解锁天数
     */
    private Long daysUntilUnlock;

    /**
     * 创建者信息
     */
    @Data
    public static class CreatorInfo {
        private Long id;
        private String nickName;
        private String avatarUrl;
    }
}
