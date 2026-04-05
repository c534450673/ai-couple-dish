package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 问候连续打卡DTO
 */
@Data
public class GreetingStreakDTO {

    /**
     * 类型: 1-早安 2-晚安
     */
    private Integer streakType;

    /**
     * 类型名称
     */
    private String streakTypeName;

    /**
     * 连续天数
     */
    private Integer streakDays;

    /**
     * 最大连续天数
     */
    private Integer maxStreakDays;

    /**
     * 是否今日已打卡
     */
    private Boolean hasCheckedToday;
}
