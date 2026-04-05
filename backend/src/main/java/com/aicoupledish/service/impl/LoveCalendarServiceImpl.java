package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.LunarCalendarUtils;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.LoveCalendarDTO;
import com.aicoupledish.service.LoveCalendarService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 恋爱日历服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LoveCalendarServiceImpl implements LoveCalendarService {

    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;
    private final AnniversaryMapper anniversaryMapper;
    private final TimeCapsuleMapper timeCapsuleMapper;
    private final HeartMomentMapper heartMomentMapper;
    private final CoupleMenuMapper coupleMenuMapper;
    private final FoodNoteMapper foodNoteMapper;
    private final WishMapper wishMapper;

    @Override
    public LoveCalendarDTO getCalendar(Long userId, Integer year, Integer month) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        if (year == null) year = LocalDate.now().getYear();
        if (month == null) month = LocalDate.now().getMonthValue();

        YearMonth yearMonth = YearMonth.of(year, month);
        LocalDate startDate = yearMonth.atDay(1);
        LocalDate endDate = yearMonth.atEndOfMonth();

        LoveCalendarDTO dto = new LoveCalendarDTO();
        dto.setYear(year);
        dto.setMonth(month);

        // 获取当月所有事件
        List<LoveCalendarDTO.CalendarEvent> allEvents = getEventsByDateRange(userId, startDate, endDate);

        // 构建日期Map
        Map<LocalDate, List<LoveCalendarDTO.CalendarEvent>> eventMap = allEvents.stream()
            .collect(Collectors.groupingBy(e -> e.getCreateTime().toLocalDate()));

        // 获取恋爱开始日期
        Couple couple = coupleMapper.selectById(user.getCoupleId());
        LocalDate loveStartDate = couple != null ? couple.getStartDate() : null;

        // 构建每一天的数据
        List<LoveCalendarDTO.DayInfo> days = new ArrayList<>();
        LocalDate today = LocalDate.now();

        for (int day = 1; day <= yearMonth.lengthOfMonth(); day++) {
            LocalDate date = LocalDate.of(year, month, day);
            LoveCalendarDTO.DayInfo dayInfo = new LoveCalendarDTO.DayInfo();
            dayInfo.setDate(date);
            dayInfo.setDayOfWeek(date.getDayOfWeek().getValue());
            dayInfo.setIsToday(date.equals(today));

            // 检查是否是恋爱纪念日
            if (loveStartDate != null) {
                dayInfo.setIsLoveAnniversary(isLoveAnniversary(loveStartDate, date));
            } else {
                dayInfo.setIsLoveAnniversary(false);
            }

            // 获取当天事件
            List<LoveCalendarDTO.CalendarEvent> dayEvents = eventMap.getOrDefault(date, new ArrayList<>());
            dayInfo.setEvents(dayEvents);
            dayInfo.setEventCount(dayEvents.size());

            days.add(dayInfo);
        }

        dto.setDays(days);

        // 统计当月事件
        LoveCalendarDTO.MonthStats stats = new LoveCalendarDTO.MonthStats();
        stats.setAnniversaryCount((int) allEvents.stream().filter(e -> "anniversary".equals(e.getEventType())).count());
        stats.setTimeCapsuleCount((int) allEvents.stream().filter(e -> "timeCapsule".equals(e.getEventType())).count());
        stats.setHeartMomentCount((int) allEvents.stream().filter(e -> "heartMoment".equals(e.getEventType())).count());
        stats.setDateCount((int) allEvents.stream().filter(e -> "menu".equals(e.getEventType()) || "note".equals(e.getEventType())).count());
        stats.setTotalEvents(allEvents.size());
        dto.setMonthStats(stats);

        return dto;
    }

    @Override
    public List<LoveCalendarDTO.CalendarEvent> getEventsByDateRange(Long userId, LocalDate startDate, LocalDate endDate) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        Long coupleId = user.getCoupleId();
        List<LoveCalendarDTO.CalendarEvent> events = new ArrayList<>();

        // 1. 获取纪念日
        List<Anniversary> anniversaries = anniversaryMapper.selectList(
            new LambdaQueryWrapper<Anniversary>()
                .eq(Anniversary::getCoupleId, coupleId)
        );

        for (Anniversary ann : anniversaries) {
            // 计算当月的纪念日日期
            LocalDate annDate = calculateAnniversaryDateInMonth(ann, startDate, endDate);
            if (annDate != null && !annDate.isBefore(startDate) && !annDate.isAfter(endDate)) {
                events.add(buildAnniversaryEvent(ann, annDate));
            }
        }

        // 2. 获取时光胶囊解锁日期
        List<TimeCapsule> capsules = timeCapsuleMapper.selectList(
            new LambdaQueryWrapper<TimeCapsule>()
                .eq(TimeCapsule::getCoupleId, coupleId)
                .ge(TimeCapsule::getUnlockDate, startDate)
                .le(TimeCapsule::getUnlockDate, endDate)
        );

        for (TimeCapsule capsule : capsules) {
            events.add(buildTimeCapsuleEvent(capsule));
        }

        // 3. 获取心动时刻
        LocalDateTime startDateTime = startDate.atStartOfDay();
        LocalDateTime endDateTime = endDate.plusDays(1).atStartOfDay();

        List<HeartMoment> moments = heartMomentMapper.selectList(
            new LambdaQueryWrapper<HeartMoment>()
                .eq(HeartMoment::getCoupleId, coupleId)
                .ge(HeartMoment::getCreateTime, startDateTime)
                .lt(HeartMoment::getCreateTime, endDateTime)
        );

        for (HeartMoment moment : moments) {
            events.add(buildHeartMomentEvent(moment));
        }

        // 4. 获取约会记录（菜单）
        List<CoupleMenu> menus = coupleMenuMapper.selectList(
            new LambdaQueryWrapper<CoupleMenu>()
                .eq(CoupleMenu::getCoupleId, coupleId)
                .isNotNull(CoupleMenu::getEatenDate)
                .ge(CoupleMenu::getEatenDate, startDate)
                .le(CoupleMenu::getEatenDate, endDate)
        );

        for (CoupleMenu menu : menus) {
            events.add(buildMenuEvent(menu));
        }

        // 5. 获取美食笔记
        List<FoodNote> notes = foodNoteMapper.selectList(
            new LambdaQueryWrapper<FoodNote>()
                .eq(FoodNote::getCoupleId, coupleId)
                .ge(FoodNote::getCreateTime, startDateTime)
                .lt(FoodNote::getCreateTime, endDateTime)
        );

        for (FoodNote note : notes) {
            events.add(buildNoteEvent(note));
        }

        // 6. 获取心愿实现
        List<Wish> wishes = wishMapper.selectList(
            new LambdaQueryWrapper<Wish>()
                .eq(Wish::getCoupleId, coupleId)
                .eq(Wish::getStatus, 1)
                .isNotNull(Wish::getAchievedDate)
                .ge(Wish::getAchievedDate, startDate)
                .le(Wish::getAchievedDate, endDate)
        );

        for (Wish wish : wishes) {
            events.add(buildWishEvent(wish));
        }

        // 按日期排序
        events.sort(Comparator.comparing(LoveCalendarDTO.CalendarEvent::getCreateTime));

        return events;
    }

    @Override
    public List<LoveCalendarDTO.CalendarEvent> getEventsByDate(Long userId, LocalDate date) {
        return getEventsByDateRange(userId, date, date);
    }

    @Override
    public List<LoveCalendarDTO.CalendarEvent> getUpcomingEvents(Long userId, Integer limit) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        LocalDate today = LocalDate.now();
        LocalDate endDate = today.plusDays(30);

        List<LoveCalendarDTO.CalendarEvent> events = getEventsByDateRange(userId, today, endDate);

        // 只返回未来的事件
        events = events.stream()
            .filter(e -> !e.getCreateTime().toLocalDate().isBefore(today))
            .collect(Collectors.toList());

        if (limit != null && events.size() > limit) {
            events = events.subList(0, limit);
        }

        return events;
    }

    @Override
    public List<LoveCalendarDTO.CalendarEvent> getTodayEvents(Long userId) {
        return getEventsByDate(userId, LocalDate.now());
    }

    @Override
    public LoveCalendarDTO getYearOverview(Long userId, Integer year) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        if (year == null) year = LocalDate.now().getYear();

        LocalDate startDate = LocalDate.of(year, 1, 1);
        LocalDate endDate = LocalDate.of(year, 12, 31);

        List<LoveCalendarDTO.CalendarEvent> allEvents = getEventsByDateRange(userId, startDate, endDate);

        LoveCalendarDTO dto = new LoveCalendarDTO();
        dto.setYear(year);

        // 构建月统计
        LoveCalendarDTO.MonthStats stats = new LoveCalendarDTO.MonthStats();
        stats.setAnniversaryCount((int) allEvents.stream().filter(e -> "anniversary".equals(e.getEventType())).count());
        stats.setTimeCapsuleCount((int) allEvents.stream().filter(e -> "timeCapsule".equals(e.getEventType())).count());
        stats.setHeartMomentCount((int) allEvents.stream().filter(e -> "heartMoment".equals(e.getEventType())).count());
        stats.setDateCount((int) allEvents.stream().filter(e -> "menu".equals(e.getEventType()) || "note".equals(e.getEventType())).count());
        stats.setTotalEvents(allEvents.size());
        dto.setMonthStats(stats);

        return dto;
    }

    /**
     * 检查是否是恋爱纪念日（每月的同一天）
     */
    private boolean isLoveAnniversary(LocalDate loveStartDate, LocalDate date) {
        if (loveStartDate == null) return false;
        return loveStartDate.getDayOfMonth() == date.getDayOfMonth();
    }

    /**
     * 计算纪念日在指定月份的日期
     */
    private LocalDate calculateAnniversaryDateInMonth(Anniversary ann, LocalDate startDate, LocalDate endDate) {
        LocalDate annDate = ann.getAnniversaryDate();
        if (annDate == null) return null;

        // 农历纪念日
        if (ann.getIsLunarDate() != null && ann.getIsLunarDate() == 1) {
            int lunarMonth = ann.getLunarMonth() != null ? ann.getLunarMonth() : annDate.getMonthValue();
            int lunarDay = ann.getLunarDay() != null ? ann.getLunarDay() : annDate.getDayOfMonth();

            // 转换为阳历
            LocalDate solarDate = LunarCalendarUtils.lunarToSolar(endDate.getYear(), lunarMonth, lunarDay, false);
            if (solarDate != null) {
                // 检查是否在当月范围内
                if (!solarDate.isBefore(startDate) && !solarDate.isAfter(endDate)) {
                    return solarDate;
                }
                // 如果不在，可能是上一年的
                solarDate = LunarCalendarUtils.lunarToSolar(startDate.getYear(), lunarMonth, lunarDay, false);
                if (solarDate != null && !solarDate.isBefore(startDate) && !solarDate.isAfter(endDate)) {
                    return solarDate;
                }
            }
            return null;
        }

        // 阳历纪念日
        int month = endDate.getMonthValue();
        int day = annDate.getDayOfMonth();

        // 处理2月29日的情况
        if (month == 2 && day == 29 && !endDate.isLeapYear()) {
            day = 28;
        }

        try {
            LocalDate result = LocalDate.of(endDate.getYear(), month, day);
            if (!result.isBefore(startDate) && !result.isAfter(endDate)) {
                return result;
            }
        } catch (Exception e) {
            // 日期无效
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

    private LoveCalendarDTO.CalendarEvent buildAnniversaryEvent(Anniversary ann, LocalDate eventDate) {
        LoveCalendarDTO.CalendarEvent event = new LoveCalendarDTO.CalendarEvent();
        event.setId(ann.getId());
        event.setEventType("anniversary");
        event.setEventTypeName("纪念日");
        event.setTitle(ann.getName());
        event.setDescription("纪念日提醒");
        event.setIcon("📅");
        event.setColor("#FF6B6B");
        event.setCreatorId(ann.getCreatorId());
        event.setCreateTime(eventDate.atTime(9, 0));

        User creator = userMapper.selectById(ann.getCreatorId());
        if (creator != null) {
            event.setCreatorName(creator.getNickName());
        }

        Map<String, Object> extra = new HashMap<>();
        extra.put("anniversaryType", ann.getAnniversaryType());
        extra.put("isLunarDate", ann.getIsLunarDate());
        event.setExtraInfo(extra);

        return event;
    }

    private LoveCalendarDTO.CalendarEvent buildTimeCapsuleEvent(TimeCapsule capsule) {
        LoveCalendarDTO.CalendarEvent event = new LoveCalendarDTO.CalendarEvent();
        event.setId(capsule.getId());
        event.setEventType("timeCapsule");
        event.setEventTypeName("时光胶囊");
        event.setTitle(capsule.getTitle() != null ? capsule.getTitle() : "时光胶囊解锁");
        event.setDescription("时光胶囊解锁日");
        event.setIcon("📦");
        event.setColor("#4ECDC4");
        event.setCreatorId(capsule.getCreatorId());
        event.setCreateTime(capsule.getUnlockDate().atTime(0, 0));

        User creator = userMapper.selectById(capsule.getCreatorId());
        if (creator != null) {
            event.setCreatorName(creator.getNickName());
        }

        return event;
    }

    private LoveCalendarDTO.CalendarEvent buildHeartMomentEvent(HeartMoment moment) {
        LoveCalendarDTO.CalendarEvent event = new LoveCalendarDTO.CalendarEvent();
        event.setId(moment.getId());
        event.setEventType("heartMoment");
        event.setEventTypeName("心动时刻");
        event.setTitle("心动时刻");
        event.setDescription(moment.getContent());
        event.setIcon("💕");
        event.setColor("#FF69B4");
        event.setCreatorId(moment.getCreatorId());
        event.setCreateTime(moment.getCreateTime());

        User creator = userMapper.selectById(moment.getCreatorId());
        if (creator != null) {
            event.setCreatorName(creator.getNickName());
        }

        return event;
    }

    private LoveCalendarDTO.CalendarEvent buildMenuEvent(CoupleMenu menu) {
        LoveCalendarDTO.CalendarEvent event = new LoveCalendarDTO.CalendarEvent();
        event.setId(menu.getId());
        event.setEventType("menu");
        event.setEventTypeName("约会记录");
        event.setTitle(menu.getRestaurantName());
        event.setDescription(menu.getDishName() != null ? menu.getDishName() : "美食约会");
        event.setIcon("🍽️");
        event.setColor("#45B7D1");
        event.setCreatorId(menu.getCreatorId());
        // eatenDate已在查询时过滤不为null，但为了安全仍做检查
        event.setCreateTime(menu.getEatenDate() != null ? menu.getEatenDate().atTime(12, 0) : LocalDateTime.now());

        User creator = userMapper.selectById(menu.getCreatorId());
        if (creator != null) {
            event.setCreatorName(creator.getNickName());
        }

        Map<String, Object> extra = new HashMap<>();
        extra.put("location", menu.getLocation());
        extra.put("rating", menu.getRating());
        event.setExtraInfo(extra);

        return event;
    }

    private LoveCalendarDTO.CalendarEvent buildNoteEvent(FoodNote note) {
        LoveCalendarDTO.CalendarEvent event = new LoveCalendarDTO.CalendarEvent();
        event.setId(note.getId());
        event.setEventType("note");
        event.setEventTypeName("美食笔记");
        event.setTitle(note.getTitle());
        String content = note.getContent();
        event.setDescription(content != null && content.length() > 50
            ? content.substring(0, 50) + "..." : (content != null ? content : ""));
        event.setIcon("📝");
        event.setColor("#96CEB4");
        event.setCreatorId(note.getAuthorId());
        event.setCreateTime(note.getCreateTime());

        User creator = userMapper.selectById(note.getAuthorId());
        if (creator != null) {
            event.setCreatorName(creator.getNickName());
        }

        return event;
    }

    private LoveCalendarDTO.CalendarEvent buildWishEvent(Wish wish) {
        LoveCalendarDTO.CalendarEvent event = new LoveCalendarDTO.CalendarEvent();
        event.setId(wish.getId());
        event.setEventType("wish");
        event.setEventTypeName("心愿实现");
        event.setTitle(wish.getTitle());
        event.setDescription("心愿达成！");
        event.setIcon("🎉");
        event.setColor("#FFD93D");
        event.setCreatorId(wish.getCreatorId());
        event.setCreateTime(wish.getAchievedDate().atTime(0, 0));

        User creator = userMapper.selectById(wish.getCreatorId());
        if (creator != null) {
            event.setCreatorName(creator.getNickName());
        }

        return event;
    }
}
