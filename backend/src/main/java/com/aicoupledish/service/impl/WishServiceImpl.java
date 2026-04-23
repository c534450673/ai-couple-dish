package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.WishMapper;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.dao.model.Wish;
import com.aicoupledish.domain.dto.WishDTO;
import com.aicoupledish.service.UserService;
import com.aicoupledish.service.WishService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 心愿单服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class WishServiceImpl implements WishService {

    private final WishMapper wishMapper;
    private final UserService userService;

    @Override
    public List<WishDTO> getWishList(Long userId) {
        User user = userService.getUserById(userId);
        if (user == null || user.getCoupleId() == null) {
            return new ArrayList<>();
        }

        List<Wish> wishes = wishMapper.selectList(
            new LambdaQueryWrapper<Wish>()
                .eq(Wish::getCoupleId, user.getCoupleId())
                .eq(Wish::getIsDeleted, 0)
                .orderByDesc(Wish::getCreateTime)
        );

        return buildWishDTOList(wishes);
    }

    @Override
    public WishDTO getWishDetail(Long userId, Long wishId) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查：确保用户属于该心愿所属的情侣
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        return convertToDTO(wish);
    }

    @Override
    @Transactional
    public Long addWish(Long userId, String wishType, String title, String description, String imageUrl, Integer priority) {
        User user = userService.getUserById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        Wish wish = new Wish();
        wish.setCoupleId(user.getCoupleId());
        wish.setCreatorId(userId);
        wish.setWishType(wishType);
        wish.setTitle(title);
        wish.setDescription(description);
        wish.setImageUrl(imageUrl);
        wish.setPriority(priority != null ? priority : 2);
        wish.setStatus(0);
        wish.setIsDeleted(0);

        wishMapper.insert(wish);
        log.info("添加心愿成功: userId={}, wishId={}", userId, wish.getId());

        return wish.getId();
    }

    @Override
    @Transactional
    public void updateWish(Long userId, Long wishId, String title, String description, String imageUrl, Integer priority) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查：确保用户属于该心愿所属的情侣
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        if (title != null) {
            wish.setTitle(title);
        }
        if (description != null) {
            wish.setDescription(description);
        }
        if (imageUrl != null) {
            wish.setImageUrl(imageUrl);
        }
        if (priority != null) {
            wish.setPriority(priority);
        }

        wishMapper.updateById(wish);
        log.info("更新心愿: userId={}, wishId={}", userId, wishId);
    }

    @Override
    @Transactional
    public void deleteWish(Long userId, Long wishId) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查：确保用户属于该心愿所属的情侣
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        wish.setIsDeleted(1);
        wishMapper.updateById(wish);
        log.info("删除心愿: userId={}, wishId={}", userId, wishId);
    }

    @Override
    @Transactional
    public void fulfillWish(Long userId, Long wishId) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查：确保用户属于该心愿所属的情侣
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        wish.setStatus(2); // 已实现
        wish.setAchievedDate(LocalDate.now());
        wishMapper.updateById(wish);
        log.info("实现心愿: userId={}, wishId={}", userId, wishId);
    }

    @Override
    @Transactional
    public void markInProgress(Long userId, Long wishId) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查：确保用户属于该心愿所属的情侣
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        // 只有非创建者（TA）才能标记为进行中
        if (wish.getCreatorId().equals(userId)) {
            throw new IllegalArgumentException("不能标记自己的心愿为进行中");
        }

        // 只有待实现状态才能标记为进行中
        if (wish.getStatus() != 0) {
            throw new IllegalArgumentException("只有待实现的心愿才能标记为进行中");
        }

        wish.setStatus(1); // 进行中
        wish.setInProgressTime(java.time.LocalDateTime.now());
        wishMapper.updateById(wish);
        log.info("标记心愿进行中: userId={}, wishId={}", userId, wishId);
    }

    @Override
    @Transactional
    public void markViewed(Long userId, Long wishId) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查：确保用户属于该心愿所属的情侣
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        // 只有非创建者（TA）才能标记已查看
        if (wish.getCreatorId().equals(userId)) {
            return; // 创建者自己查看不需要记录
        }

        // 如果已经查看过，不重复记录
        if (wish.getViewerId() != null) {
            return;
        }

        wish.setViewerId(userId);
        wish.setViewTime(java.time.LocalDateTime.now());
        wishMapper.updateById(wish);
        log.info("标记心愿已查看: userId={}, wishId={}", userId, wishId);
    }

    @Override
    @Transactional
    public void cancelInProgress(Long userId, Long wishId) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查：确保用户属于该心愿所属的情侣
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        // 只有进行中状态才能取消
        if (wish.getStatus() != 1) {
            throw new IllegalArgumentException("只有进行中的心愿才能取消");
        }

        wish.setStatus(0); // 回到待实现
        wish.setInProgressTime(null);
        wishMapper.updateById(wish);
        log.info("取消心愿进行中状态: userId={}, wishId={}", userId, wishId);
    }

    /**
     * 批量构建WishDTO - 优化N+1查询
     */
    private List<WishDTO> buildWishDTOList(List<Wish> wishes) {
        if (wishes == null || wishes.isEmpty()) {
            return new ArrayList<>();
        }

        // 收集所有需要的用户ID
        java.util.Set<Long> userIds = wishes.stream()
                .map(Wish::getCreatorId)
                .filter(id -> id != null)
                .collect(java.util.stream.Collectors.toSet());

        // 批量查询用户信息
        final java.util.Map<Long, User> userMap;
        if (!userIds.isEmpty()) {
            // 使用 UserService 的批量查询方法
            userMap = userService.getUsersByIds(userIds);
        } else {
            userMap = new java.util.HashMap<>();
        }

        return wishes.stream()
                .map(wish -> convertToDTO(wish, userMap))
                .collect(Collectors.toList());
    }

    private WishDTO convertToDTO(Wish wish) {
        return convertToDTO(wish, null);
    }

    private WishDTO convertToDTO(Wish wish, java.util.Map<Long, User> userMap) {
        WishDTO dto = new WishDTO();
        dto.setId(wish.getId());
        dto.setCoupleId(wish.getCoupleId());
        dto.setCreatorId(wish.getCreatorId());
        dto.setWishType(wish.getWishType());
        dto.setTitle(wish.getTitle());
        dto.setDescription(wish.getDescription());
        dto.setImageUrl(wish.getImageUrl());
        dto.setPriority(wish.getPriority());
        dto.setStatus(wish.getStatus());
        dto.setTargetDate(wish.getTargetDate());
        dto.setAchievedDate(wish.getAchievedDate());
        dto.setCreateTime(wish.getCreateTime());

        // 新增字段
        dto.setViewerId(wish.getViewerId());
        dto.setViewTime(wish.getViewTime());
        dto.setInProgressTime(wish.getInProgressTime());

        // 转换类型名称
        dto.setWishTypeName(getWishTypeName(wish.getWishType()));
        dto.setPriorityName(getPriorityName(wish.getPriority()));
        dto.setStatusName(getStatusName(wish.getStatus()));

        // 计算进行中持续天数
        if (wish.getInProgressTime() != null) {
                long days = java.time.temporal.ChronoUnit.DAYS.between(
                    wish.getInProgressTime(),
                    java.time.LocalDateTime.now()
                );
                dto.setInProgressDays((int) days);
            }

        // 是否被TA看过
        dto.setViewed(wish.getViewerId() != null);

        // 获取创建者信息 - 使用缓存的userMap避免N+1查询
        if (wish.getCreatorId() != null) {
            User creator;
            if (userMap != null) {
                creator = userMap.get(wish.getCreatorId());
            } else {
                creator = userService.getUserById(wish.getCreatorId());
            }
            if (creator != null) {
                dto.setCreatorName(creator.getNickName());
                dto.setCreatorAvatar(creator.getAvatarUrl());
            }
        }

        return dto;
    }

    private String getWishTypeName(String wishType) {
        if (wishType == null) return "其他";
        switch (wishType) {
            case "restaurant": return "餐厅";
            case "dish": return "菜品";
            case "recipe": return "食谱";
            default: return "其他";
        }
    }

    private String getPriorityName(Integer priority) {
        if (priority == null) return "中";
        switch (priority) {
            case 1: return "低";
            case 2: return "中";
            case 3: return "高";
            default: return "中";
        }
    }

    private String getStatusName(Integer status) {
        if (status == null) return "待实现";
        switch (status) {
            case 0: return "待实现";
            case 1: return "进行中";
            case 2: return "已实现";
            case 3: return "已过期";
            default: return "待实现";
        }
    }

    @Override
    @Transactional
    public void unfulfillWish(Long userId, Long wishId) {
        User user = userService.getUserById(userId);
        Wish wish = wishMapper.selectById(wishId);
        if (wish == null) {
            throw BusinessException.WISH_NOT_FOUND;
        }

        // 权限检查
        if (user.getCoupleId() == null || !wish.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.WISH_NOT_PERMISSION;
        }

        // 只有已实现状态才能撤销
        if (wish.getStatus() != 2) {
            throw new IllegalArgumentException("只有已实现的心愿才能撤销");
        }

        wish.setStatus(1); // 回到进行中
        wish.setAchievedDate(null);
        wishMapper.updateById(wish);
        log.info("撤销实现心愿: userId={}, wishId={}", userId, wishId);
    }
}