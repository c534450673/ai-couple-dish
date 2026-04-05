package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 问候连续打卡记录表
 */
@Data
@TableName("t_greeting_streak")
public class GreetingStreak implements Serializable {

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
     * 类型: 1-早安连续 2-晚安连续
     */
    private Integer streakType;

    /**
     * 连续天数
     */
    private Integer streakDays;

    /**
     * 最大连续天数
     */
    private Integer maxStreakDays;

    /**
     * 最后打卡日期
     */
    private LocalDate lastDate;

    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
