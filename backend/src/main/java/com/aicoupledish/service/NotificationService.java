package com.aicoupledish.service;

import com.aicoupledish.dao.model.Notification;
import java.util.List;

/**
 * 通知服务接口
 */
public interface NotificationService {

    /**
     * 获取通知列表
     */
    List<Notification> getNotificationList(Long userId, Integer type, Integer page, Integer pageSize);

    /**
     * 获取未读通知数量
     */
    Integer getUnreadCount(Long userId);

    /**
     * 标记通知已读
     */
    void markAsRead(Long userId, Long notificationId);

    /**
     * 标记所有通知已读
     */
    void markAllAsRead(Long userId);

    /**
     * 删除通知
     */
    void deleteNotification(Long userId, Long notificationId);

    /**
     * 发送通知
     */
    void sendNotification(Long userId, Integer type, String title, String content, Long relatedId, String relatedType);

    /**
     * 发送情侣互动通知
     */
    void sendCoupleNotification(Long coupleId, Long senderId, Integer type, String title, String content, Long relatedId, String relatedType);
}