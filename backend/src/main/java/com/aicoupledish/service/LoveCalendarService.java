package com.aicoupledish.service;

import com.aicoupledish.domain.dto.LoveCalendarDTO;

import java.time.LocalDate;
import java.util.List;

/**
 * 恋爱日历服务接口
 */
public interface LoveCalendarService {

    /**
     * 获取指定月份的日历数据
     */
    LoveCalendarDTO getCalendar(Long userId, Integer year, Integer month);

    /**
     * 获取指定日期范围的事件
     */
    List<LoveCalendarDTO.CalendarEvent> getEventsByDateRange(Long userId, LocalDate startDate, LocalDate endDate);

    /**
     * 获取指定日期的事件
     */
    List<LoveCalendarDTO.CalendarEvent> getEventsByDate(Long userId, LocalDate date);

    /**
     * 获取即将到来的事件（未来30天）
     */
    List<LoveCalendarDTO.CalendarEvent> getUpcomingEvents(Long userId, Integer limit);

    /**
     * 获取今日事件
     */
    List<LoveCalendarDTO.CalendarEvent> getTodayEvents(Long userId);

    /**
     * 获取年度概览
     */
    LoveCalendarDTO getYearOverview(Long userId, Integer year);
}
