package com.aicoupledish.domain.dto;

import lombok.Data;
import java.util.List;

/**
 * 投喂DTO
 */
@Data
public class FeedDTO {

    private Long id;
    private Long coupleId;
    private Long senderId;
    private String senderName;
    private String senderAvatar;
    private Long receiverId;
    private String receiverName;
    private String feedType;
    private String feedTypeName;
    private String content;
    private List<String> imageUrls;
    private String message;
    private Integer status;
    private String statusName;
    private String expireTime;
    private String createTime;
    private String receiveTime;
    private String rejectReason;
}