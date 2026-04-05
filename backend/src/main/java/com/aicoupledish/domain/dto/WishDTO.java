package com.aicoupledish.domain.dto;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 心愿单DTO
 */
@Data
public class WishDTO {

    private Long id;
    private Long coupleId;
    private Long creatorId;
    private String creatorName;
    private String creatorAvatar;
    private String wishType;
    private String wishTypeName;
    private String title;
    private String description;
    private String imageUrl;
    private Integer priority;
    private String priorityName;
    private Integer status;
    private String statusName;
    private LocalDate targetDate;
    private LocalDate achievedDate;
    private LocalDateTime createTime;

    /**
     * 查看者ID
     */
    private Long viewerId;

    /**
     * 查看时间
     */
    private LocalDateTime viewTime;

    /**
     * 进行中开始时间
     */
    private LocalDateTime inProgressTime;

    /**
     * 是否被TA看过
     */
    private Boolean viewed;

    /**
     * 进行中持续天数
     */
    private Integer inProgressDays;
}
