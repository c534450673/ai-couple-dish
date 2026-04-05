package com.aicoupledish.domain.dto;

import lombok.Data;

import java.util.List;

/**
 * 今日投喂DTO
 */
@Data
public class TodayFeedDTO {

    /**
     * 今日是否已发送
     */
    private Boolean sentToday;

    /**
     * 今日是否收到
     */
    private Boolean receivedToday;

    /**
     * 待领取的投喂
     */
    private FeedDTO pendingFeed;

    /**
     * 今日已发送次数
     */
    private Integer sentCount;

    /**
     * 今日剩余发送次数
     */
    private Integer remainingCount;

    /**
     * 今日已发送的投喂类型列表
     */
    private List<String> sentTypes;

    /**
     * 可发送的投喂类型列表
     */
    private List<String> availableTypes;
}