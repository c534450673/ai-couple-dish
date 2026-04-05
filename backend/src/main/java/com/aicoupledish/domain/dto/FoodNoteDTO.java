package com.aicoupledish.domain.dto;

import lombok.Data;
import java.util.List;

/**
 * 美食笔记DTO
 */
@Data
public class FoodNoteDTO {

    private Long id;
    private Long coupleId;
    private Long authorId;
    private String authorName;
    private String authorAvatar;
    private String title;
    private String content;
    private String location;
    private Double latitude;
    private Double longitude;
    private Boolean isAnniversaryLinked;
    private Long anniversaryId;
    private String anniversaryName;
    private Integer viewCount;
    private Integer likeCount;
    private Integer commentCount;
    private List<String> photoUrls;
    private String createTime;
    private Boolean isLiked;
    private Boolean isAuthor;
}