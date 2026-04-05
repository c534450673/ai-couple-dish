package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.LoveCalendarDTO;
import com.aicoupledish.service.LoveCalendarService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.time.LocalDate;
import java.util.List;

/**
 * 恋爱日历控制器
 */
@Api(tags = "专属恋爱日历模块")
@RestController
@RequestMapping("/loveCalendar")
@RequiredArgsConstructor
public class LoveCalendarController {

    private final LoveCalendarService loveCalendarService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取指定月份的日历数据")
    @GetMapping("/month")
    public Result<LoveCalendarDTO> getCalendar(
            @ApiParam(value = "年份，默认当前年")
            @RequestParam(required = false) Integer year,
            @ApiParam(value = "月份，默认当前月")
            @RequestParam(required = false) Integer month) {
        Long userId = getCurrentUserId();
        LoveCalendarDTO dto = loveCalendarService.getCalendar(userId, year, month);
        return Result.success(dto);
    }

    @ApiOperation("获取指定日期的事件")
    @GetMapping("/events/date")
    public Result<List<LoveCalendarDTO.CalendarEvent>> getEventsByDate(
            @ApiParam(value = "日期", required = true)
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        Long userId = getCurrentUserId();
        List<LoveCalendarDTO.CalendarEvent> events = loveCalendarService.getEventsByDate(userId, date);
        return Result.success(events);
    }

    @ApiOperation("获取指定日期范围的事件")
    @GetMapping("/events/range")
    public Result<List<LoveCalendarDTO.CalendarEvent>> getEventsByDateRange(
            @ApiParam(value = "开始日期", required = true)
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @ApiParam(value = "结束日期", required = true)
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        Long userId = getCurrentUserId();
        List<LoveCalendarDTO.CalendarEvent> events = loveCalendarService.getEventsByDateRange(userId, startDate, endDate);
        return Result.success(events);
    }

    @ApiOperation("获取即将到来的事件")
    @GetMapping("/events/upcoming")
    public Result<List<LoveCalendarDTO.CalendarEvent>> getUpcomingEvents(
            @ApiParam(value = "数量限制，默认10")
            @RequestParam(required = false, defaultValue = "10") Integer limit) {
        Long userId = getCurrentUserId();
        List<LoveCalendarDTO.CalendarEvent> events = loveCalendarService.getUpcomingEvents(userId, limit);
        return Result.success(events);
    }

    @ApiOperation("获取今日事件")
    @GetMapping("/events/today")
    public Result<List<LoveCalendarDTO.CalendarEvent>> getTodayEvents() {
        Long userId = getCurrentUserId();
        List<LoveCalendarDTO.CalendarEvent> events = loveCalendarService.getTodayEvents(userId);
        return Result.success(events);
    }

    @ApiOperation("获取年度概览")
    @GetMapping("/year/overview")
    public Result<LoveCalendarDTO> getYearOverview(
            @ApiParam(value = "年份，默认当前年")
            @RequestParam(required = false) Integer year) {
        Long userId = getCurrentUserId();
        LoveCalendarDTO dto = loveCalendarService.getYearOverview(userId, year);
        return Result.success(dto);
    }

    private Long getCurrentUserId() {
        String token = request.getHeader("Authorization");
        if (token == null || token.isEmpty()) {
            throw new BusinessException(9001, "请先登录");
        }
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }
        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            throw new BusinessException(9001, "无效的登录凭证");
        }
        return userId;
    }
}
