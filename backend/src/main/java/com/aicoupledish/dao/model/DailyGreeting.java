package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 每日问候表
 */
@Data
@TableName("t_daily_greeting")
public class DailyGreeting implements Serializable {

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
     * 用户ID
     */
    private Long userId;

    /**
     * 类型: 1-早安 2-晚安
     */
    private Integer greetingType;

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
     * 是否删除
     */
    @TableLogic
    private Integer isDeleted;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
