package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 每日问候DTO
 */
@Data
public class DailyGreetingDTO {

    private Long id;

    /**
     * 类型: 1-早安 2-晚安
     */
    private Integer greetingType;

    /**
     * 类型名称
     */
    private String greetingTypeName;

    /**
     * 文字内容
     */
    private String content;

    /**
     * 语音文件URL
     */
    private String voiceUrl;

    /**
     * 语音时长(秒)
     */
    private Integer voiceDuration;

    /**
     * 问候日期
     */
    private LocalDate greetingDate;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 发送者信息
     */
    private UserInfo sender;

    /**
     * 连续打卡天数
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

    /**
     * 双方今日打卡状态
     */
    private BothCheckStatus bothCheckStatus;

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
     * 双方打卡状态
     */
    @Data
    public static class BothCheckStatus {
        /**
         * 我是否已打卡
         */
        private Boolean myChecked;

        /**
         * 对方是否已打卡
         */
        private Boolean partnerChecked;

        /**
         * 我的打卡时间
         */
        private LocalDateTime myCheckTime;

        /**
         * 对方打卡时间
         */
        private LocalDateTime partnerCheckTime;
    }
}
