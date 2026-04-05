package com.aicoupledish.service.impl;

import cn.hutool.json.JSONUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.FeedMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Feed;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.FeedDTO;
import com.aicoupledish.domain.dto.TodayFeedDTO;
import com.aicoupledish.domain.req.SendFeedReq;
import com.aicoupledish.service.FeedService;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 投喂服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class FeedServiceImpl implements FeedService {

    private final FeedMapper feedMapper;
    private final UserMapper userMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    @Override
    public TodayFeedDTO getTodayFeedStatus(Long userId) {
        User user = getUserById(userId);
        TodayFeedDTO dto = new TodayFeedDTO();

        LocalDate today = LocalDate.now();
        LocalDateTime startOfDay = today.atStartOfDay();
        LocalDateTime endOfDay = today.plusDays(1).atStartOfDay();

        // 检查今日是否已发送
        Long sentCount = feedMapper.selectCount(
            new LambdaQueryWrapper<Feed>()
                .eq(Feed::getSenderId, userId)
                .eq(Feed::getStatus, 0)
                .between(Feed::getCreateTime, startOfDay, endOfDay)
        );
        dto.setSentToday(sentCount != null && sentCount > 0);

        // 检查今日是否收到待领取的投喂
        Feed pendingFeed = feedMapper.selectOne(
            new LambdaQueryWrapper<Feed>()
                .eq(Feed::getReceiverId, userId)
                .eq(Feed::getStatus, 0)
                .gt(Feed::getExpireTime, LocalDateTime.now())
                .orderByDesc(Feed::getCreateTime)
                .last("LIMIT 1")
        );
        dto.setReceivedToday(pendingFeed != null);

        if (pendingFeed != null) {
            dto.setPendingFeed(buildFeedDTO(pendingFeed));
        }

        return dto;
    }

    @Override
    @Transactional
    public Long sendFeed(Long userId, SendFeedReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 获取伴侣ID
        User partner = getPartner(user);
        if (partner == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 检查今日该类型的投喂是否已发送（每天每种类型只能发一次）
        LocalDate today = LocalDate.now();
        LocalDateTime startOfDay = today.atStartOfDay();
        LocalDateTime endOfDay = today.plusDays(1).atStartOfDay();

        Long todayTypeSentCount = feedMapper.selectCount(
            new LambdaQueryWrapper<Feed>()
                .eq(Feed::getSenderId, userId)
                .eq(Feed::getFeedType, req.getFeedType())
                .ge(Feed::getCreateTime, startOfDay)
                .lt(Feed::getCreateTime, endOfDay)
        );

        if (todayTypeSentCount != null && todayTypeSentCount > 0) {
            String typeName = getFeedTypeName(req.getFeedType());
            throw new BusinessException(9006, "今日已发送过" + typeName + "类型的投喂");
        }

        // 检查今日总投喂次数（最多3次）
        Long todaySentCount = feedMapper.selectCount(
            new LambdaQueryWrapper<Feed>()
                .eq(Feed::getSenderId, userId)
                .ge(Feed::getCreateTime, startOfDay)
                .lt(Feed::getCreateTime, endOfDay)
        );

        if (todaySentCount != null && todaySentCount >= 3) {
            throw new BusinessException(9007, "今日投喂次数已达上限（3次）");
        }

        Feed feed = new Feed();
        feed.setCoupleId(user.getCoupleId());
        feed.setSenderId(userId);
        feed.setReceiverId(partner.getId());
        feed.setFeedType(req.getFeedType());
        feed.setContent(req.getContent());
        feed.setImageUrls(req.getImageUrls() != null ? JSONUtil.toJsonStr(req.getImageUrls()) : null);
        feed.setMessage(req.getMessage());
        feed.setStatus(0);
        feed.setExpireTime(LocalDateTime.now().plusHours(24));

        feedMapper.insert(feed);

        // 发送通知
        if (notificationService != null) {
            String feedTypeName = getFeedTypeName(req.getFeedType());
            notificationService.sendNotification(partner.getId(), 2, "🍰 收到投喂",
                "你的伴侣给你送了一份" + feedTypeName + "，快去看看吧！", feed.getId(), "feed");
        }

        log.info("发送投喂: userId={}, feedId={}, type={}", userId, feed.getId(), req.getFeedType());
        return feed.getId();
    }

    @Override
    public List<FeedDTO> getReceivedFeeds(Long userId) {
        List<Feed> feeds = feedMapper.selectList(
            new LambdaQueryWrapper<Feed>()
                .eq(Feed::getReceiverId, userId)
                .orderByDesc(Feed::getCreateTime)
        );
        return buildFeedDTOList(feeds);
    }

    @Override
    public List<FeedDTO> getSentFeeds(Long userId) {
        List<Feed> feeds = feedMapper.selectList(
            new LambdaQueryWrapper<Feed>()
                .eq(Feed::getSenderId, userId)
                .orderByDesc(Feed::getCreateTime)
        );
        return buildFeedDTOList(feeds);
    }

    @Override
    @Transactional
    public void acceptFeed(Long userId, Long feedId) {
        Feed feed = feedMapper.selectById(feedId);
        if (feed == null) {
            throw BusinessException.FEED_NOT_FOUND;
        }

        if (!feed.getReceiverId().equals(userId)) {
            throw BusinessException.FEED_CANNOT_ACCEPT;
        }

        if (feed.getStatus() != 0) {
            throw BusinessException.FEED_EXPIRED;
        }

        if (feed.getExpireTime().isBefore(LocalDateTime.now())) {
            throw BusinessException.FEED_EXPIRED;
        }

        feed.setStatus(1); // 已领取
        feed.setReceiveTime(LocalDateTime.now());
        feedMapper.updateById(feed);

        // 通知发送者
        if (notificationService != null) {
            notificationService.sendNotification(feed.getSenderId(), 2, "💕 投喂被接受",
                "你的投喂被接受了，快去看看TA的反应吧！", feedId, "feed");
        }

        log.info("接受投喂: userId={}, feedId={}", userId, feedId);
    }

    @Override
    @Transactional
    public void rejectFeed(Long userId, Long feedId, String reason) {
        Feed feed = feedMapper.selectById(feedId);
        if (feed == null) {
            throw BusinessException.FEED_NOT_FOUND;
        }

        if (!feed.getReceiverId().equals(userId)) {
            throw BusinessException.FEED_CANNOT_ACCEPT;
        }

        feed.setStatus(2); // 已拒绝
        feed.setRejectReason(reason);
        feedMapper.updateById(feed);

        // 通知发送者
        if (notificationService != null) {
            notificationService.sendNotification(feed.getSenderId(), 2, "😢 投喂被拒绝",
                "你的投喂被拒绝了：" + (reason != null ? reason : "TA说不想吃"), feedId, "feed");
        }

        log.info("拒绝投喂: userId={}, feedId={}, reason={}", userId, feedId, reason);
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private User getPartner(User user) {
        if (user.getCoupleId() == null) {
            return null;
        }

        // 查询情侣关系中的另一个用户
        List<User> users = userMapper.selectList(
            new LambdaQueryWrapper<User>()
                .eq(User::getCoupleId, user.getCoupleId())
                .ne(User::getId, user.getId())
        );

        return users.isEmpty() ? null : users.get(0);
    }

    private String getFeedTypeName(String feedType) {
        switch (feedType) {
            case "meal": return "正餐";
            case "dessert": return "甜品";
            case "snack": return "小吃";
            case "drink": return "饮品";
            default: return "美食";
        }
    }

    private FeedDTO buildFeedDTO(Feed feed) {
        return buildFeedDTO(feed, null);
    }

    private FeedDTO buildFeedDTO(Feed feed, java.util.Map<Long, User> userMap) {
        FeedDTO dto = new FeedDTO();
        dto.setId(feed.getId());
        dto.setCoupleId(feed.getCoupleId());
        dto.setSenderId(feed.getSenderId());
        dto.setReceiverId(feed.getReceiverId());
        dto.setFeedType(feed.getFeedType());
        dto.setFeedTypeName(getFeedTypeName(feed.getFeedType()));
        dto.setContent(feed.getContent());
        dto.setImageUrls(feed.getImageUrls() != null ? JSONUtil.toList(feed.getImageUrls(), String.class) : new ArrayList<>());
        dto.setMessage(feed.getMessage());
        dto.setStatus(feed.getStatus());
        dto.setStatusName(getStatusName(feed.getStatus()));
        dto.setExpireTime(feed.getExpireTime() != null ? feed.getExpireTime().toString() : null);
        dto.setCreateTime(feed.getCreateTime() != null ? feed.getCreateTime().toString() : null);
        dto.setReceiveTime(feed.getReceiveTime() != null ? feed.getReceiveTime().toString() : null);
        dto.setRejectReason(feed.getRejectReason());

        // 获取发送者信息 - 使用缓存的userMap避免N+1查询
        User sender;
        if (userMap != null) {
            sender = userMap.get(feed.getSenderId());
        } else {
            sender = userMapper.selectById(feed.getSenderId());
        }
        if (sender != null) {
            dto.setSenderName(sender.getNickName());
            dto.setSenderAvatar(sender.getAvatarUrl());
        }

        return dto;
    }

    /**
     * 批量构建FeedDTO - 优化N+1查询
     */
    private List<FeedDTO> buildFeedDTOList(List<Feed> feeds) {
        if (feeds == null || feeds.isEmpty()) {
            return new ArrayList<>();
        }

        // 收集所有需要的用户ID
        java.util.Set<Long> userIds = feeds.stream()
                .map(Feed::getSenderId)
                .collect(java.util.stream.Collectors.toSet());

        // 批量查询用户信息
        if (!userIds.isEmpty()) {
            List<User> users = userMapper.selectBatchIds(userIds);
            java.util.Map<Long, User> userMap = users.stream()
                    .collect(Collectors.toMap(User::getId, u -> u));

            return feeds.stream()
                    .map(feed -> buildFeedDTO(feed, userMap))
                    .collect(Collectors.toList());
        }

        return feeds.stream()
                .map(this::buildFeedDTO)
                .collect(Collectors.toList());
    }

    private String getStatusName(Integer status) {
        switch (status) {
            case 0: return "待领取";
            case 1: return "已领取";
            case 2: return "已拒绝";
            case 3: return "已过期";
            default: return "未知";
        }
    }
}