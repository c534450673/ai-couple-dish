package com.aicoupledish.domain.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.util.List;

/**
 * 菜单DTO
 */
@Data
public class MenuDTO {

    private Long id;
    private Long coupleId;
    private Long creatorId;
    private String creatorName;
    private String creatorAvatar;
    private String restaurantName;
    private String dishName;
    private String dishCategory;
    private BigDecimal price;
    private String location;
    private BigDecimal latitude;
    private BigDecimal longitude;
    private String note;
    private Integer rating;
    private List<Long> eaterIds;
    private String eaterNames;
    private String eatenDate;
    private Integer status;
    private String statusName;
    private Integer likeCount;
    private Boolean isFavorite;
    private String photoUrls;
    private Integer photoCount;
    private Long anniversaryId;
    private String createTime;
    private Boolean isLiked;
    private Double distance;
}