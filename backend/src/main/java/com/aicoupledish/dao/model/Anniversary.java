package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 纪念日表
 */
@Data
@TableName("t_anniversary")
public class Anniversary implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 情侣ID
     */
    private Long coupleId;

    /**
     * 创建者ID
     */
    private Long creatorId;

    /**
     * 纪念日名称
     */
    private String name;

    /**
     * 纪念日日期
     */
    private LocalDate anniversaryDate;

    /**
     * 是否农历日期：0-阳历 1-农历
     */
    private Integer isLunarDate;

    /**
     * 农历月（用于农历纪念日）
     */
    private Integer lunarMonth;

    /**
     * 农历日（用于农历纪念日）
     */
    private Integer lunarDay;

    /**
     * 类型：1-相识 2-恋爱 3-表白 4-其他
     */
    private Integer anniversaryType;

    /**
     * 提前提醒天数
     */
    private Integer remindDaysBefore;

    /**
     * 是否自动提醒
     */
    private Integer autoRemind;

    /**
     * 最后提醒日期
     */
    private LocalDate lastRemindDate;

    /**
     * 提醒渠道：逗号分隔，如 "app,wechat,sms"
     */
    private String remindChannels;

    /**
     * 提醒时间（小时），如 9 表示早上9点
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

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /**
     * 是否删除
     */
    @TableLogic
    private Integer isDeleted;
}