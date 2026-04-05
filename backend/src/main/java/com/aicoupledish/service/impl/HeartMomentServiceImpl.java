package com.aicoupledish.service.impl;

import cn.hutool.core.util.StrUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.HeartMomentMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.HeartMoment;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.HeartMomentDTO;
import com.aicoupledish.domain.req.HeartMomentReq;
import com.aicoupledish.service.HeartMomentService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;

/**
 * 心动时刻服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class HeartMomentServiceImpl implements HeartMomentService {

    private final HeartMomentMapper heartMomentMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    @Override
    @Transactional
    public Long createHeartMoment(Long userId, HeartMomentReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        HeartMoment moment = new HeartMoment();
        moment.setCoupleId(user.getCoupleId());
        moment.setCreatorId(userId);
        moment.setMomentType(req.getMomentType());
        moment.setContent(req.getContent());
        moment.setMediaUrl(req.getMediaUrl());

        heartMomentMapper.insert(moment);
        log.info("创建心动时刻: userId={}, momentId={}", userId, moment.getId());

        return moment.getId();
    }

    @Override
    public List<HeartMomentDTO> getHeartMomentList(Long userId, Long page, Long pageSize) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        if (page == null || page < 1) page = 1L;
        if (pageSize == null || pageSize < 1) pageSize = 20L;

        List<HeartMoment> moments = heartMomentMapper.selectList(
            new LambdaQueryWrapper<HeartMoment>()
                .eq(HeartMoment::getCoupleId, user.getCoupleId())
                .orderByDesc(HeartMoment::getCreateTime)
                .last("LIMIT " + ((page - 1) * pageSize) + ", " + pageSize)
        );

        return moments.stream().map(this::buildDTO).collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void deleteHeartMoment(Long userId, Long momentId) {
        HeartMoment moment = heartMomentMapper.selectById(momentId);

        if (moment == null) {
            throw new IllegalArgumentException("心动时刻不存在");
        }

        if (!moment.getCreatorId().equals(userId)) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        heartMomentMapper.deleteById(momentId);
        log.info("删除心动时刻: userId={}, momentId={}", userId, momentId);
    }

    @Override
    public HeartMomentDTO getRandomHeartMoment(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 获取总数
        Long count = heartMomentMapper.selectCount(
            new LambdaQueryWrapper<HeartMoment>()
                .eq(HeartMoment::getCoupleId, user.getCoupleId())
        );

        if (count == null || count == 0) {
            return null;
        }

        // 随机获取一条 - 确保offset不超出范围
        int total = count.intValue();
        int offset = new Random().nextInt(total);
        HeartMoment moment = heartMomentMapper.selectOne(
            new LambdaQueryWrapper<HeartMoment>()
                .eq(HeartMoment::getCoupleId, user.getCoupleId())
                .last("LIMIT " + offset + ", 1")
        );

        return moment != null ? buildDTO(moment) : null;
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private HeartMomentDTO buildDTO(HeartMoment moment) {
        HeartMomentDTO dto = new HeartMomentDTO();
        dto.setId(moment.getId());
        dto.setMomentType(moment.getMomentType());
        dto.setContent(moment.getContent());
        dto.setMediaUrl(moment.getMediaUrl());
        dto.setCreateTime(moment.getCreateTime());
        dto.setTimeDesc(getTimeDesc(moment.getCreateTime()));

        // 创建者信息
        User creator = userMapper.selectById(moment.getCreatorId());
        if (creator != null) {
            HeartMomentDTO.CreatorInfo creatorInfo = new HeartMomentDTO.CreatorInfo();
            creatorInfo.setId(creator.getId());
            creatorInfo.setNickName(creator.getNickName());
            creatorInfo.setAvatarUrl(creator.getAvatarUrl());
            dto.setCreator(creatorInfo);
        }

        return dto;
    }

    private String getTimeDesc(LocalDateTime time) {
        if (time == null) return "";

        long minutes = ChronoUnit.MINUTES.between(time, LocalDateTime.now());

        if (minutes < 1) {
            return "刚刚";
        } else if (minutes < 60) {
            return minutes + "分钟前";
        } else if (minutes < 60 * 24) {
            return (minutes / 60) + "小时前";
        } else if (minutes < 60 * 24 * 7) {
            return (minutes / (60 * 24)) + "天前";
        } else {
            return time.toLocalDate().toString();
        }
    }
}
