package com.aicoupledish.service;

import com.aicoupledish.domain.dto.FeedDTO;
import com.aicoupledish.domain.dto.TodayFeedDTO;
import com.aicoupledish.domain.req.SendFeedReq;

import java.util.List;

/**
 * 投喂服务接口
 */
public interface FeedService {

    /**
     * 获取今日投喂状态
     */
    TodayFeedDTO getTodayFeedStatus(Long userId);

    /**
     * 发送投喂
     */
    Long sendFeed(Long userId, SendFeedReq req);

    /**
     * 获取收到的投喂列表
     */
    List<FeedDTO> getReceivedFeeds(Long userId);

    /**
     * 获取发出的投喂列表
     */
    List<FeedDTO> getSentFeeds(Long userId);

    /**
     * 接受投喂
     */
    void acceptFeed(Long userId, Long feedId);

    /**
     * 拒绝投喂
     */
    void rejectFeed(Long userId, Long feedId, String reason);
}