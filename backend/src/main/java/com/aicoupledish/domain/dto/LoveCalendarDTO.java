package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 恋爱日历DTO
 */
@Data
public class LoveCalendarDTO {

    /**
     * 年份
     */
    private Integer year;

    /**
     * 月份
     */
    private Integer month;

    /**
     * 当月天数
     */
    private List<DayInfo> days;

    /**
     * 当月事件统计
     */
    private MonthStats monthStats;

    /**
     * 日信息
     */
    @Data
    public static class DayInfo {
        /**
         * 日期
         */
        private LocalDate date;

        /**
         * 星期几 (1-7)
         */
        private Integer dayOfWeek;

        /**
         * 是否今天
         */
        private Boolean isToday;

        /**
         * 是否恋爱纪念日
         */
        private Boolean isLoveAnniversary;

        /**
         * 当天的事件列表
         */
        private List<CalendarEvent> events;

        /**
         * 事件数量
         */
        private Integer eventCount;
    }

    /**
     * 日历事件
     */
    @Data
    public static class CalendarEvent {
        /**
         * 事件ID
         */
        private Long id;

        /**
         * 事件类型: anniversary/timeCapsule/heartMoment/menu/note/wish
         */
        private String eventType;

        /**
         * 事件类型名称
         */
        private String eventTypeName;

        /**
         * 事件标题
         */
        private String title;

        /**
         * 事件描述
         */
        private String description;

        /**
         * 事件图标
         */
        private String icon;

        /**
         * 事件颜色
         */
        private String color;

        /**
         * 创建者ID
         */
        private Long creatorId;

        /**
         * 创建者名称
         */
        private String creatorName;

        /**
         * 创建时间
         */
        private LocalDateTime createTime;

        /**
         * 额外信息
         */
        private Map<String, Object> extraInfo;
    }

    /**
     * 月统计
     */
    @Data
    public static class MonthStats {
        /**
         * 纪念日数量
         */
        private Integer anniversaryCount;

        /**
         * 时光胶囊解锁数量
         */
        private Integer timeCapsuleCount;

        /**
         * 心动时刻数量
         */
        private Integer heartMomentCount;

        /**
         * 约会记录数量
         */
        private Integer dateCount;

        /**
         * 总事件数
         */
        private Integer totalEvents;
    }

    /**
     * 日期范围请求
     */
    @Data
    public static class DateRangeReq {
        private LocalDate startDate;
        private LocalDate endDate;
    }
}
