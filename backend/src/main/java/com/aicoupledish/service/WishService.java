package com.aicoupledish.service;

import com.aicoupledish.domain.dto.WishDTO;

import java.util.List;

/**
 * 心愿单服务接口
 */
public interface WishService {

    /**
     * 获取心愿单列表
     */
    List<WishDTO> getWishList(Long userId);

    /**
     * 获取心愿单详情
     */
    WishDTO getWishDetail(Long userId, Long wishId);

    /**
     * 添加心愿
     */
    Long addWish(Long userId, String wishType, String title, String description, String imageUrl, Integer priority);

    /**
     * 更新心愿
     */
    void updateWish(Long userId, Long wishId, String title, String description, String imageUrl, Integer priority);

    /**
     * 删除心愿
     */
    void deleteWish(Long userId, Long wishId);

    /**
     * 实现心愿
     */
    void fulfillWish(Long userId, Long wishId);

    /**
     * 标记心愿为进行中（TA已看到并计划中）
     */
    void markInProgress(Long userId, Long wishId);

    /**
     * 标记心愿已查看
     */
    void markViewed(Long userId, Long wishId);

    /**
     * 取消进行中状态（回到待实现）
     */
    void cancelInProgress(Long userId, Long wishId);
}
