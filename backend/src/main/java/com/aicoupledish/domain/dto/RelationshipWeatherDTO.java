package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 关系气象站DTO
 */
@Data
public class RelationshipWeatherDTO {

    private Long id;

    /**
     * 天气等级
     */
    private String weatherLevel;

    /**
     * 天气等级名称
     */
    private String weatherLevelName;

    /**
     * 天气图标
     */
    private String weatherIcon;

    /**
     * 天气描述
     */
    private String weatherDescription;

    /**
     * 互动分数
     */
    private Integer interactionScore;

    /**
     * 距上次互动天数
     */
    private Integer daysSinceLastInteraction;

    /**
     * 恋爱温度
     */
    private Integer temperatureScore;

    /**
     * 是否有预警
     */
    private Boolean hasAlert;

    /**
     * 预警类型
     */
    private String alertType;

    /**
     * 预警消息
     */
    private String alertMessage;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 互动记录
     */
    private List<InteractionRecord> interactions;

    /**
     * 改善建议
     */
    private List<ImprovementSuggestion> suggestions;

    /**
     * 互动记录
     */
    @Data
    public static class InteractionRecord {
        private String type;
        private String description;
        private LocalDateTime time;
        private Integer score;
    }

    /**
     * 改善建议
     */
    @Data
    public static class ImprovementSuggestion {
        private String type;
        private String title;
        private String description;
        private String action;
    }

    /**
     * 天气预报
     */
    @Data
    public static class WeatherForecast {
        private String date;
        private String weatherLevel;
        private String weatherIcon;
        private Integer predictedScore;
    }
}
