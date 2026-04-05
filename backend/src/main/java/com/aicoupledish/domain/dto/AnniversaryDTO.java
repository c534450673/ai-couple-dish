package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 纪念日DTO
 */
@Data
public class AnniversaryDTO {

    private Long id;
    private String name;
    private String anniversaryDate;
    private Integer anniversaryType;
    private String typeName;
    private Integer remindDaysBefore;
    private Integer autoRemind;

    /**
     * 是否农历日期
     */
    private Boolean isLunarDate;

    /**
     * 农历月
     */
    private Integer lunarMonth;

    /**
     * 农历日
     */
    private Integer lunarDay;

    /**
     * 农历日期名称（如：甲辰年正月初一）
     */
    private String lunarDateName;

    /**
     * 距离天数（用于显示倒计时）
     */
    private Integer daysUntil;

    /**
     * 是否已过
     */
    private Boolean isPast;

    /**
     * 提醒渠道
     */
    private String remindChannels;

    /**
     * 提醒时间（小时）
     */
    private Integer remindHour;

    /**
     * 是否启用微信提醒
     */
    private Integer wechatRemindEnabled;

    /**
     * 是否启用短信提醒
     */
    private Integer smsRemindEnabled;

    /**
     * 是否启用APP推送
     */
    private Integer appRemindEnabled;
}