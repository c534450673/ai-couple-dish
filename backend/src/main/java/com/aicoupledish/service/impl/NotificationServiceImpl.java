package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.NotificationMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Notification;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 通知服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NotificationServiceImpl implements NotificationService {

    private final NotificationMapper notificationMapper;
    private final UserMapper userMapper;

    @Override
    public List<Notification> getNotificationList(Long userId, Integer type, Integer page, Integer pageSize) {
        LambdaQueryWrapper<Notification> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(Notification::getUserId, userId);
        if (type != null) {
            queryWrapper.eq(Notification::getType, type);
        }
        queryWrapper.orderByDesc(Notification::getCreateTime);

        if (page != null && pageSize != null && page > 0 && pageSize > 0) {
            int validPage = Math.max(1, page);
            int validPageSize = Math.max(1, pageSize);
            queryWrapper.last("LIMIT " + (validPage - 1) * validPageSize + ", " + validPageSize);
        }

        return notificationMapper.selectList(queryWrapper);
    }

    @Override
    public Integer getUnreadCount(Long userId) {
        Long count = notificationMapper.selectCount(
            new LambdaQueryWrapper<Notification>()
                .eq(Notification::getUserId, userId)
                .eq(Notification::getIsRead, 0)
        );
        return count != null ? count.intValue() : 0;
    }

    @Override
    @Transactional
    public void markAsRead(Long userId, Long notificationId) {
        Notification notification = notificationMapper.selectById(notificationId);
        if (notification == null || !notification.getUserId().equals(userId)) {
            return;
        }

        notification.setIsRead(1);
        notification.setReadTime(LocalDateTime.now());
        notificationMapper.updateById(notification);
    }

    @Override
    @Transactional
    public void markAllAsRead(Long userId) {
        Notification notification = new Notification();
        notification.setIsRead(1);
        notification.setReadTime(LocalDateTime.now());

        notificationMapper.update(notification,
            new LambdaUpdateWrapper<Notification>()
                .eq(Notification::getUserId, userId)
                .eq(Notification::getIsRead, 0)
        );
    }

    @Override
    @Transactional
    public void deleteNotification(Long userId, Long notificationId) {
        Notification notification = notificationMapper.selectById(notificationId);
        if (notification == null || !notification.getUserId().equals(userId)) {
            return;
        }

        notificationMapper.deleteById(notificationId);
    }

    @Override
    @Transactional
    public void sendNotification(Long userId, Integer type, String title, String content, Long relatedId, String relatedType) {
        Notification notification = new Notification();
        notification.setUserId(userId);
        notification.setType(type);
        notification.setTitle(title);
        notification.setContent(content);
        notification.setRelatedId(relatedId);
        notification.setRelatedType(relatedType);
        notification.setIsRead(0);

        notificationMapper.insert(notification);
        log.info("发送通知: userId={}, title={}", userId, title);
    }

    @Override
    @Transactional
    public void sendCoupleNotification(Long coupleId, Long senderId, Integer type, String title, String content, Long relatedId, String relatedType) {
        // 获取情侣双方的用户ID
        List<User> users = userMapper.selectList(
            new LambdaQueryWrapper<User>()
                .eq(User::getCoupleId, coupleId)
        );

        for (User user : users) {
            // 不通知发送者自己
            if (!user.getId().equals(senderId)) {
                sendNotification(user.getId(), type, title, content, relatedId, relatedType);
            }
        }
    }
}