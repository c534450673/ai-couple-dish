package com.aicoupledish.service.impl;

import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.TimeCapsuleMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.TimeCapsule;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.TimeCapsuleDTO;
import com.aicoupledish.domain.req.TimeCapsuleReq;
import com.aicoupledish.service.NotificationService;
import com.aicoupledish.service.TimeCapsuleService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 时光胶囊服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TimeCapsuleServiceImpl implements TimeCapsuleService {

    private final TimeCapsuleMapper timeCapsuleMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    @Override
    @Transactional
    public Long createTimeCapsule(Long userId, TimeCapsuleReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 验证解锁日期
        if (req.getUnlockDate().isBefore(LocalDate.now().plusDays(1))) {
            throw new IllegalArgumentException("解锁日期必须至少是明天");
        }

        TimeCapsule capsule = new TimeCapsule();
        capsule.setCoupleId(user.getCoupleId());
        capsule.setCreatorId(userId);
        capsule.setCapsuleType(req.getCapsuleType());
        capsule.setTitle(req.getTitle());
        capsule.setContent(req.getContent());
        capsule.setUnlockDate(req.getUnlockDate());
        capsule.setStatus(0); // 待解锁

        if (req.getMediaUrls() != null && !req.getMediaUrls().isEmpty()) {
            capsule.setMediaUrls(JSONUtil.toJsonStr(req.getMediaUrls()));
        }

        timeCapsuleMapper.insert(capsule);
        log.info("创建时光胶囊: userId={}, capsuleId={}, unlockDate={}", userId, capsule.getId(), req.getUnlockDate());

        // 发送通知给伴侣
        Couple couple = coupleMapper.selectById(user.getCoupleId());
        if (notificationService != null && couple != null) {
            Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
            notificationService.sendNotification(partnerId, 1, "📦 新的时光胶囊",
                "TA给你留下了一个时光胶囊，将在" + req.getUnlockDate() + "解锁", capsule.getId(), "time_capsule");
        }

        return capsule.getId();
    }

    @Override
    public List<TimeCapsuleDTO> getTimeCapsuleList(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<TimeCapsule> capsules = timeCapsuleMapper.selectList(
            new LambdaQueryWrapper<TimeCapsule>()
                .eq(TimeCapsule::getCoupleId, user.getCoupleId())
                .orderByAsc(TimeCapsule::getUnlockDate)
        );

        if (capsules.isEmpty()) {
            return new ArrayList<>();
        }

        // 批量加载创建者信息（修复N+1查询）
        Set<Long> creatorIds = capsules.stream()
                .map(TimeCapsule::getCreatorId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = creatorIds.isEmpty() ? Collections.emptyMap() :
                userMapper.selectBatchIds(creatorIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u, (a, b) -> a));

        return capsules.stream()
                .map(capsule -> buildDTOWithCache(capsule, userMap))
                .collect(Collectors.toList());
    }

    @Override
    public TimeCapsuleDTO getTimeCapsuleDetail(Long userId, Long capsuleId) {
        User user = getUserById(userId);
        TimeCapsule capsule = timeCapsuleMapper.selectById(capsuleId);

        if (capsule == null) {
            throw new IllegalArgumentException("时光胶囊不存在");
        }

        if (!capsule.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        TimeCapsuleDTO dto = buildDTO(capsule);

        // 如果未解锁且未到解锁日期，隐藏内容
        if (capsule.getStatus() == 0 && capsule.getUnlockDate().isAfter(LocalDate.now())) {
            dto.setContent("🔒 胶囊尚未解锁");
            dto.setMediaUrls(null);
        }

        return dto;
    }

    @Override
    @Transactional
    public TimeCapsuleDTO unlockTimeCapsule(Long userId, Long capsuleId) {
        User user = getUserById(userId);
        TimeCapsule capsule = timeCapsuleMapper.selectById(capsuleId);

        if (capsule == null) {
            throw new IllegalArgumentException("时光胶囊不存在");
        }

        if (!capsule.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        if (capsule.getStatus() == 1) {
            throw new IllegalArgumentException("时光胶囊已解锁");
        }

        if (capsule.getUnlockDate().isAfter(LocalDate.now())) {
            throw new IllegalArgumentException("尚未到达解锁日期");
        }

        capsule.setStatus(1);
        capsule.setUnlockTime(LocalDateTime.now());
        timeCapsuleMapper.updateById(capsule);

        log.info("解锁时光胶囊: userId={}, capsuleId={}", userId, capsuleId);

        // 通知创建者
        if (notificationService != null) {
            notificationService.sendNotification(capsule.getCreatorId(), 2, "🎉 时光胶囊已解锁",
                "你的时光胶囊已被TA解锁", capsuleId, "time_capsule");
        }

        return buildDTO(capsule);
    }

    @Override
    @Transactional
    public void deleteTimeCapsule(Long userId, Long capsuleId) {
        User user = getUserById(userId);
        TimeCapsule capsule = timeCapsuleMapper.selectById(capsuleId);

        if (capsule == null) {
            throw new IllegalArgumentException("时光胶囊不存在");
        }

        // 只有创建者可以删除
        if (!capsule.getCreatorId().equals(userId)) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        timeCapsuleMapper.deleteById(capsuleId);
        log.info("删除时光胶囊: userId={}, capsuleId={}", userId, capsuleId);
    }

    @Override
    public List<TimeCapsuleDTO> getPendingTimeCapsules(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<TimeCapsule> capsules = timeCapsuleMapper.selectList(
            new LambdaQueryWrapper<TimeCapsule>()
                .eq(TimeCapsule::getCoupleId, user.getCoupleId())
                .eq(TimeCapsule::getStatus, 0)
                .le(TimeCapsule::getUnlockDate, LocalDate.now())
        );

        if (capsules.isEmpty()) {
            return new ArrayList<>();
        }

        // 批量加载创建者信息（修复N+1查询）
        Set<Long> creatorIds = capsules.stream()
                .map(TimeCapsule::getCreatorId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = creatorIds.isEmpty() ? Collections.emptyMap() :
                userMapper.selectBatchIds(creatorIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u, (a, b) -> a));

        return capsules.stream()
                .map(capsule -> buildDTOWithCache(capsule, userMap))
                .collect(Collectors.toList());
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private TimeCapsuleDTO buildDTO(TimeCapsule capsule) {
        return buildDTOWithCache(capsule, null);
    }

    /**
     * 构建DTO（使用缓存的用户数据，避免N+1查询）
     */
    private TimeCapsuleDTO buildDTOWithCache(TimeCapsule capsule, Map<Long, User> userMap) {
        TimeCapsuleDTO dto = new TimeCapsuleDTO();
        dto.setId(capsule.getId());
        dto.setCapsuleType(capsule.getCapsuleType());
        dto.setTitle(capsule.getTitle());
        dto.setContent(capsule.getContent());
        dto.setUnlockDate(capsule.getUnlockDate());
        dto.setStatus(capsule.getStatus());
        dto.setCreateTime(capsule.getCreateTime());
        dto.setUnlockTime(capsule.getUnlockTime());

        // 状态名称
        dto.setStatusName(capsule.getStatus() == 0 ? "待解锁" : "已解锁");

        // 解锁天数计算
        LocalDate today = LocalDate.now();
        if (capsule.getStatus() == 0) {
            dto.setDaysUntilUnlock(ChronoUnit.DAYS.between(today, capsule.getUnlockDate()));
            dto.setCanUnlock(!capsule.getUnlockDate().isAfter(today));
        } else {
            dto.setDaysUntilUnlock(0L);
            dto.setCanUnlock(false);
        }

        // 媒体URLs
        if (StrUtil.isNotBlank(capsule.getMediaUrls())) {
            dto.setMediaUrls(JSONUtil.toList(capsule.getMediaUrls(), String.class));
        }

        // 创建者信息（使用缓存或单独查询）
        User creator = userMap != null ? userMap.get(capsule.getCreatorId()) : userMapper.selectById(capsule.getCreatorId());
        if (creator != null) {
            TimeCapsuleDTO.CreatorInfo creatorInfo = new TimeCapsuleDTO.CreatorInfo();
            creatorInfo.setId(creator.getId());
            creatorInfo.setNickName(creator.getNickName());
            creatorInfo.setAvatarUrl(creator.getAvatarUrl());
            dto.setCreator(creatorInfo);
        }

        return dto;
    }
}
