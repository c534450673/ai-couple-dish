package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 心情记录DTO
 */
@Data
public class MoodRecordDTO {

    private Long id;

    /**
     * 心情类型
     */
    private String moodType;

    /**
     * 心情类型名称
     */
    private String moodTypeName;

    /**
     * 心情描述
     */
    private String description;

    /**
     * 心情图标
     */
    private String moodIcon;

    /**
     * 心情颜色
     */
    private String moodColor;

    /**
     * 记录日期
     */
    private LocalDate recordDate;

    /**
     * 是否已读
     */
    private Boolean isRead;

    /**
     * 阅读时间
     */
    private LocalDateTime readTime;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 发送者信息
     */
    private UserInfo sender;

    /**
     * 用户信息
     */
    @Data
    public static class UserInfo {
        private Long id;
        private String nickName;
        private String avatarUrl;
    }

    /**
     * 心情类型定义
     */
    @Data
    public static class MoodType {
        private String type;
        private String name;
        private String icon;
        private String color;
        private String description;
    }

    /**
     * 心情统计
     */
    @Data
    public static class MoodStats {
        /**
         * 本月记录次数
         */
        private Integer monthCount;

        /**
         * 本周记录次数
         */
        private Integer weekCount;

        /**
         * 今日记录次数
         */
        private Integer todayCount;

        /**
         * 心情分布
         */
        private List<MoodDistribution> distribution;
    }

    /**
     * 心情分布
     */
    @Data
    public static class MoodDistribution {
        private String moodType;
        private String moodTypeName;
        private Integer count;
        private Double percentage;
    }
}
