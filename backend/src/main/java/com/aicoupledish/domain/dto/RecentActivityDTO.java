package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 最近动态DTO
 */
@Data
public class RecentActivityDTO {

    private Long id;
    private String type;
    private String typeName;
    private String title;
    private String content;
    private String imageUrl;
    private Long creatorId;
    private String creatorName;
    private String creatorAvatar;
    private String createTime;
}