package com.aicoupledish.service.impl;

import cn.hutool.core.util.StrUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.DailyGreetingMapper;
import com.aicoupledish.dao.mapper.GreetingStreakMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.DailyGreeting;
import com.aicoupledish.dao.model.GreetingStreak;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.DailyGreetingDTO;
import com.aicoupledish.domain.dto.GreetingStreakDTO;
import com.aicoupledish.domain.req.DailyGreetingReq;
import com.aicoupledish.service.DailyGreetingService;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 每日问候服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DailyGreetingServiceImpl implements DailyGreetingService {

    private final DailyGreetingMapper dailyGreetingMapper;
    private final GreetingStreakMapper greetingStreakMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    /**
     * 问候类型：早安
     */
    private static final int GREETING_TYPE_MORNING = 1;

    /**
     * 问候类型：晚安
     */
    private static final int GREETING_TYPE_NIGHT = 2;
    private static final ZoneId BUSINESS_ZONE = ZoneId.of("Asia/Shanghai");
    private static final String ACTIVE_GREETING_UNIQUE_INDEX =
        "uk_daily_greeting_active_user_type_date";

    @Override
    @Transactional
    public Long sendGreeting(Long userId, DailyGreetingReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 检查今日是否已发送该类型问候
        LocalDate today = LocalDate.now(BUSINESS_ZONE);
        DailyGreeting existing = dailyGreetingMapper.selectOne(
            new LambdaQueryWrapper<DailyGreeting>()
                .eq(DailyGreeting::getUserId, userId)
                .eq(DailyGreeting::getGreetingType, req.getGreetingType())
                .eq(DailyGreeting::getGreetingDate, today)
        );

        if (existing != null) {
            throw BusinessException.GREETING_ALREADY_SENT;
        }

        // 创建问候记录
        DailyGreeting greeting = new DailyGreeting();
        greeting.setCoupleId(user.getCoupleId());
        greeting.setUserId(userId);
        greeting.setGreetingType(req.getGreetingType());
        greeting.setContent(req.getContent());
        greeting.setVoiceUrl(req.getVoiceUrl());
        greeting.setVoiceDuration(req.getVoiceDuration());
        greeting.setGreetingDate(today);

        try {
            dailyGreetingMapper.insert(greeting);
        } catch (DuplicateKeyException exception) {
            String causeMessage = exception.getMostSpecificCause().getMessage();
            if (causeMessage == null || !causeMessage.contains(ACTIVE_GREETING_UNIQUE_INDEX)) {
                throw exception;
            }
            log.warn(
                "event=daily_greeting_send_rejected operation=sendGreeting result=rejected "
                    + "errorCode=8602 userId={} greetingType={} greetingDate={}",
                userId, req.getGreetingType(), today
            );
            throw BusinessException.GREETING_ALREADY_SENT;
        }

        // 更新连续打卡记录
        updateStreak(user.getCoupleId(), userId, req.getGreetingType(), today);

        log.info(
            "event=daily_greeting_send_completed operation=sendGreeting result=success "
                + "errorCode=NONE userId={} greetingType={} greetingId={}",
            userId, req.getGreetingType(), greeting.getId()
        );

        // 发送通知给伴侣
        if (notificationService != null) {
            String greetingName = req.getGreetingType() == GREETING_TYPE_MORNING ? "早安" : "晚安";
            Couple couple = coupleMapper.selectById(user.getCoupleId());
            if (couple != null) {
                Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
                notificationService.sendNotification(partnerId, 1,
                    "☀️ " + greetingName + "心动打卡",
                    "TA给你发来了" + greetingName + "问候，快去看看吧~",
                    greeting.getId(), "daily_greeting");
            }
        }

        return greeting.getId();
    }

    @Override
    public DailyGreetingDTO getTodayStatus(Long userId, Integer greetingType) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        LocalDate today = LocalDate.now();
        DailyGreeting greeting = dailyGreetingMapper.selectOne(
            new LambdaQueryWrapper<DailyGreeting>()
                .eq(DailyGreeting::getUserId, userId)
                .eq(DailyGreeting::getGreetingType, greetingType)
                .eq(DailyGreeting::getGreetingDate, today)
        );

        DailyGreetingDTO dto = new DailyGreetingDTO();
        dto.setGreetingType(greetingType);
        dto.setGreetingTypeName(greetingType == GREETING_TYPE_MORNING ? "早安" : "晚安");
        dto.setGreetingDate(today);
        dto.setHasCheckedToday(greeting != null);

        if (greeting != null) {
            dto.setId(greeting.getId());
            dto.setContent(greeting.getContent());
            dto.setVoiceUrl(greeting.getVoiceUrl());
            dto.setVoiceDuration(greeting.getVoiceDuration());
            dto.setCreateTime(greeting.getCreateTime());

            User sender = userMapper.selectById(userId);
            if (sender != null) {
                DailyGreetingDTO.UserInfo userInfo = new DailyGreetingDTO.UserInfo();
                userInfo.setId(sender.getId());
                userInfo.setNickName(sender.getNickName());
                userInfo.setAvatarUrl(sender.getAvatarUrl());
                dto.setSender(userInfo);
            }
        }

        // 获取连续打卡天数
        GreetingStreak streak = greetingStreakMapper.selectOne(
            new LambdaQueryWrapper<GreetingStreak>()
                .eq(GreetingStreak::getCoupleId, user.getCoupleId())
                .eq(GreetingStreak::getStreakType, greetingType)
        );

        if (streak != null) {
            dto.setStreakDays(streak.getStreakDays());
            dto.setMaxStreakDays(streak.getMaxStreakDays());
        } else {
            dto.setStreakDays(0);
            dto.setMaxStreakDays(0);
        }

        return dto;
    }

    @Override
    public List<DailyGreetingDTO> getGreetingHistory(Long userId, Integer greetingType, Integer limit) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<DailyGreeting> greetings = dailyGreetingMapper.selectList(
            new LambdaQueryWrapper<DailyGreeting>()
                .eq(DailyGreeting::getCoupleId, user.getCoupleId())
                .eq(greetingType != null, DailyGreeting::getGreetingType, greetingType)
                .orderByDesc(DailyGreeting::getGreetingDate)
                .last("LIMIT " + (limit != null ? limit : 30))
        );

        return greetings.stream().map(this::buildDTO).collect(Collectors.toList());
    }

    @Override
    public GreetingStreakDTO getStreakInfo(Long userId, Integer streakType) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        GreetingStreak streak = greetingStreakMapper.selectOne(
            new LambdaQueryWrapper<GreetingStreak>()
                .eq(GreetingStreak::getCoupleId, user.getCoupleId())
                .eq(GreetingStreak::getStreakType, streakType)
        );

        GreetingStreakDTO dto = new GreetingStreakDTO();
        dto.setStreakType(streakType);
        dto.setStreakTypeName(streakType == GREETING_TYPE_MORNING ? "早安" : "晚安");

        if (streak != null) {
            dto.setStreakDays(streak.getStreakDays());
            dto.setMaxStreakDays(streak.getMaxStreakDays());

            // 检查今日是否已打卡
            LocalDate today = LocalDate.now();
            dto.setHasCheckedToday(today.equals(streak.getLastDate()));
        } else {
            dto.setStreakDays(0);
            dto.setMaxStreakDays(0);
            dto.setHasCheckedToday(false);
        }

        return dto;
    }

    @Override
    public DailyGreetingDTO getBothCheckStatus(Long userId, Integer greetingType) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        Couple couple = coupleMapper.selectById(user.getCoupleId());
        if (couple == null) {
            throw BusinessException.COUPLE_NOT_FOUND;
        }

        Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
        LocalDate today = LocalDate.now();

        // 查询我的打卡记录
        DailyGreeting myGreeting = dailyGreetingMapper.selectOne(
            new LambdaQueryWrapper<DailyGreeting>()
                .eq(DailyGreeting::getUserId, userId)
                .eq(DailyGreeting::getGreetingType, greetingType)
                .eq(DailyGreeting::getGreetingDate, today)
        );

        // 查询对方的打卡记录
        DailyGreeting partnerGreeting = dailyGreetingMapper.selectOne(
            new LambdaQueryWrapper<DailyGreeting>()
                .eq(DailyGreeting::getUserId, partnerId)
                .eq(DailyGreeting::getGreetingType, greetingType)
                .eq(DailyGreeting::getGreetingDate, today)
        );

        DailyGreetingDTO dto = new DailyGreetingDTO();
        dto.setGreetingType(greetingType);
        dto.setGreetingTypeName(greetingType == GREETING_TYPE_MORNING ? "早安" : "晚安");
        dto.setGreetingDate(today);

        DailyGreetingDTO.BothCheckStatus bothStatus = new DailyGreetingDTO.BothCheckStatus();
        bothStatus.setMyChecked(myGreeting != null);
        bothStatus.setPartnerChecked(partnerGreeting != null);
        bothStatus.setMyCheckTime(myGreeting != null ? myGreeting.getCreateTime() : null);
        bothStatus.setPartnerCheckTime(partnerGreeting != null ? partnerGreeting.getCreateTime() : null);
        dto.setBothCheckStatus(bothStatus);

        // 获取连续打卡信息
        GreetingStreak streak = greetingStreakMapper.selectOne(
            new LambdaQueryWrapper<GreetingStreak>()
                .eq(GreetingStreak::getCoupleId, user.getCoupleId())
                .eq(GreetingStreak::getStreakType, greetingType)
        );

        if (streak != null) {
            dto.setStreakDays(streak.getStreakDays());
            dto.setMaxStreakDays(streak.getMaxStreakDays());
        } else {
            dto.setStreakDays(0);
            dto.setMaxStreakDays(0);
        }

        return dto;
    }

    @Override
    public DailyGreetingDTO getGreetingDetail(Long userId, Long greetingId) {
        User user = getUserById(userId);
        DailyGreeting greeting = dailyGreetingMapper.selectById(greetingId);

        if (greeting == null) {
            throw new IllegalArgumentException("问候记录不存在");
        }

        if (!greeting.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        return buildDTO(greeting);
    }

    /**
     * 更新连续打卡记录
     */
    private void updateStreak(Long coupleId, Long userId, Integer greetingType, LocalDate today) {
        int affectedRows = greetingStreakMapper.upsert(coupleId, greetingType, today);
        log.debug(
            "event=daily_greeting_streak_upsert_completed operation=updateStreak result=success "
                + "errorCode=NONE userId={} coupleId={} greetingType={} greetingDate={} "
                + "affectedRows={}",
            userId, coupleId, greetingType, today, affectedRows
        );
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private DailyGreetingDTO buildDTO(DailyGreeting greeting) {
        DailyGreetingDTO dto = new DailyGreetingDTO();
        dto.setId(greeting.getId());
        dto.setGreetingType(greeting.getGreetingType());
        dto.setGreetingTypeName(greeting.getGreetingType() == GREETING_TYPE_MORNING ? "早安" : "晚安");
        dto.setContent(greeting.getContent());
        dto.setVoiceUrl(greeting.getVoiceUrl());
        dto.setVoiceDuration(greeting.getVoiceDuration());
        dto.setGreetingDate(greeting.getGreetingDate());
        dto.setCreateTime(greeting.getCreateTime());

        // 发送者信息
        User sender = userMapper.selectById(greeting.getUserId());
        if (sender != null) {
            DailyGreetingDTO.UserInfo userInfo = new DailyGreetingDTO.UserInfo();
            userInfo.setId(sender.getId());
            userInfo.setNickName(sender.getNickName());
            userInfo.setAvatarUrl(sender.getAvatarUrl());
            dto.setSender(userInfo);
        }

        return dto;
    }
}
