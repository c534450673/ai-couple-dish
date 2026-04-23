package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.MoodRecordMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.MoodRecord;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.MoodRecordDTO;
import com.aicoupledish.domain.req.MoodRecordReq;
import com.aicoupledish.service.MoodRecordService;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 心情记录服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MoodRecordServiceImpl implements MoodRecordService {

    private final MoodRecordMapper moodRecordMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;
    private final NotificationService notificationService;

    /**
     * 心情类型配置
     */
    private static final List<MoodTypeInfo> MOOD_TYPES = new ArrayList<MoodTypeInfo>() {{
        add(new MoodTypeInfo("happy", "开心", "😊", "#FFD700", "今天心情很好"));
        add(new MoodTypeInfo("love", "爱你", "❤️", "#FF69B4", "想对TA说爱你"));
        add(new MoodTypeInfo("miss_you", "想你", "🥺", "#87CEEB", "好想TA"));
        add(new MoodTypeInfo("tired", "疲惫", "😴", "#9370DB", "今天有点累"));
        add(new MoodTypeInfo("upset", "烦躁", "😤", "#FF6347", "心情不太好"));
        add(new MoodTypeInfo("sad", "难过", "😢", "#6495ED", "有点伤心"));
        add(new MoodTypeInfo("angry", "生气", "😠", "#DC143C", "很生气"));
        add(new MoodTypeInfo("anxious", "焦虑", "😰", "#808080", "有点焦虑"));
    }};

    @Override
    @Transactional
    public Long sendMood(Long userId, MoodRecordReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        MoodTypeInfo moodInfo = getMoodInfo(req.getMoodType());
        if (moodInfo == null) {
            throw new IllegalArgumentException("无效的心情类型");
        }

        MoodRecord record = new MoodRecord();
        record.setUserId(userId);
        record.setCoupleId(user.getCoupleId());
        record.setMoodType(req.getMoodType());
        record.setDescription(req.getDescription());
        record.setMoodIcon(moodInfo.icon);
        record.setMoodColor(moodInfo.color);
        record.setRecordDate(LocalDate.now());
        record.setIsRead(0);
        moodRecordMapper.insert(record);

        log.info("发送心情: userId={}, type={}", userId, req.getMoodType());

        // 发送通知给伴侣
        Couple couple = coupleMapper.selectById(user.getCoupleId());
        if (couple != null) {
            Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
            notificationService.sendNotification(partnerId, 2,
                "💌 心情投递", "TA给你投递了一份心情: " + moodInfo.name,
                record.getId(), "mood_record");
        }

        return record.getId();
    }

    @Override
    public List<MoodRecordDTO> getTodayMoods(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        LocalDate today = LocalDate.now();
        List<MoodRecord> records = moodRecordMapper.selectList(
            new LambdaQueryWrapper<MoodRecord>()
                .eq(MoodRecord::getCoupleId, user.getCoupleId())
                .eq(MoodRecord::getRecordDate, today)
                .orderByDesc(MoodRecord::getCreateTime)
        );

        return records.stream().map(this::buildDTO).collect(Collectors.toList());
    }

    @Override
    public List<MoodRecordDTO> getMoodHistory(Long userId, Integer limit) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<MoodRecord> records = moodRecordMapper.selectList(
            new LambdaQueryWrapper<MoodRecord>()
                .eq(MoodRecord::getCoupleId, user.getCoupleId())
                .orderByDesc(MoodRecord::getRecordDate)
                .orderByDesc(MoodRecord::getCreateTime)
                .last("LIMIT " + (limit != null ? limit : 30))
        );

        return records.stream().map(this::buildDTO).collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void markAsRead(Long userId, Long moodId) {
        MoodRecord record = moodRecordMapper.selectById(moodId);
        if (record == null) {
            throw new IllegalArgumentException("心情记录不存在");
        }

        User user = getUserById(userId);
        if (!record.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        if (record.getIsRead() == 0) {
            record.setIsRead(1);
            record.setReadTime(LocalDateTime.now());
            moodRecordMapper.updateById(record);
        }
    }

    @Override
    public MoodRecordDTO.MoodStats getMoodStats(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        MoodRecordDTO.MoodStats stats = new MoodRecordDTO.MoodStats();
        LocalDate today = LocalDate.now();

        // 今日记录数
        Long todayCount = moodRecordMapper.selectCount(
            new LambdaQueryWrapper<MoodRecord>()
                .eq(MoodRecord::getCoupleId, user.getCoupleId())
                .eq(MoodRecord::getRecordDate, today)
        );
        stats.setTodayCount(todayCount != null ? todayCount.intValue() : 0);

        // 本周记录数
        LocalDate weekStart = today.minusDays(today.getDayOfWeek().getValue() - 1);
        Long weekCount = moodRecordMapper.selectCount(
            new LambdaQueryWrapper<MoodRecord>()
                .eq(MoodRecord::getCoupleId, user.getCoupleId())
                .ge(MoodRecord::getRecordDate, weekStart)
        );
        stats.setWeekCount(weekCount != null ? weekCount.intValue() : 0);

        // 本月记录数
        LocalDate monthStart = YearMonth.now().atDay(1);
        Long monthCount = moodRecordMapper.selectCount(
            new LambdaQueryWrapper<MoodRecord>()
                .eq(MoodRecord::getCoupleId, user.getCoupleId())
                .ge(MoodRecord::getRecordDate, monthStart)
        );
        stats.setMonthCount(monthCount != null ? monthCount.intValue() : 0);

        // 心情分布
        List<MoodRecord> monthRecords = moodRecordMapper.selectList(
            new LambdaQueryWrapper<MoodRecord>()
                .eq(MoodRecord::getCoupleId, user.getCoupleId())
                .ge(MoodRecord::getRecordDate, monthStart)
        );

        List<MoodRecordDTO.MoodDistribution> distribution = new ArrayList<>();
        int total = monthRecords.size();
        for (MoodTypeInfo info : MOOD_TYPES) {
            int count = (int) monthRecords.stream().filter(r -> r.getMoodType().equals(info.type)).count();
            if (count > 0) {
                MoodRecordDTO.MoodDistribution dist = new MoodRecordDTO.MoodDistribution();
                dist.setMoodType(info.type);
                dist.setMoodTypeName(info.name);
                dist.setCount(count);
                dist.setPercentage(total > 0 ? (double) count / total * 100 : 0);
                distribution.add(dist);
            }
        }
        stats.setDistribution(distribution);

        return stats;
    }

    @Override
    public List<MoodRecordDTO.MoodType> getMoodTypes() {
        return MOOD_TYPES.stream().map(info -> {
            MoodRecordDTO.MoodType type = new MoodRecordDTO.MoodType();
            type.setType(info.type);
            type.setName(info.name);
            type.setIcon(info.icon);
            type.setColor(info.color);
            type.setDescription(info.description);
            return type;
        }).collect(Collectors.toList());
    }

    @Override
    public Integer getUnreadCount(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            return 0;
        }

        Long count = moodRecordMapper.selectCount(
            new LambdaQueryWrapper<MoodRecord>()
                .eq(MoodRecord::getCoupleId, user.getCoupleId())
                .ne(MoodRecord::getUserId, userId)
                .eq(MoodRecord::getIsRead, 0)
        );

        return count != null ? count.intValue() : 0;
    }

    @Override
    public MoodRecordDTO getMoodDetail(Long userId, Long moodId) {
        MoodRecord record = moodRecordMapper.selectById(moodId);
        if (record == null) {
            throw new IllegalArgumentException("心情记录不存在");
        }

        User user = getUserById(userId);
        if (!record.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        return buildDTO(record);
    }

    private MoodTypeInfo getMoodInfo(String moodType) {
        for (MoodTypeInfo info : MOOD_TYPES) {
            if (info.type.equals(moodType)) {
                return info;
            }
        }
        return null;
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private MoodRecordDTO buildDTO(MoodRecord record) {
        MoodRecordDTO dto = new MoodRecordDTO();
        dto.setId(record.getId());
        dto.setMoodType(record.getMoodType());

        MoodTypeInfo info = getMoodInfo(record.getMoodType());
        if (info != null) {
            dto.setMoodTypeName(info.name);
        }

        dto.setDescription(record.getDescription());
        dto.setMoodIcon(record.getMoodIcon());
        dto.setMoodColor(record.getMoodColor());
        dto.setRecordDate(record.getRecordDate());
        dto.setIsRead(record.getIsRead() == 1);
        dto.setReadTime(record.getReadTime());
        dto.setCreateTime(record.getCreateTime());

        User sender = userMapper.selectById(record.getUserId());
        if (sender != null) {
            MoodRecordDTO.UserInfo userInfo = new MoodRecordDTO.UserInfo();
            userInfo.setId(sender.getId());
            userInfo.setNickName(sender.getNickName());
            userInfo.setAvatarUrl(sender.getAvatarUrl());
            dto.setSender(userInfo);
        }

        return dto;
    }

    /**
     * 心情类型信息
     */
    private static class MoodTypeInfo {
        String type;
        String name;
        String icon;
        String color;
        String description;

        MoodTypeInfo(String type, String name, String icon, String color, String description) {
            this.type = type;
            this.name = name;
            this.icon = icon;
            this.color = color;
            this.description = description;
        }
    }
}
