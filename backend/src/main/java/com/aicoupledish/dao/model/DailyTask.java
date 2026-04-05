package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 每日情侣任务表
 */
@Data
@TableName("t_daily_task")
public class DailyTask implements Serializable {

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
     * 任务日期
     */
    private LocalDate taskDate;

    /**
     * 任务类型
     */
    private String taskType;

    /**
     * 任务名称
     */
    private String taskName;

    /**
     * 任务描述
     */
    private String taskDescription;

    /**
     * 目标数量
     */
    private Integer targetCount;

    /**
     * 奖励养分
     */
    private Integer rewardNutrient;

    /**
     * 状态: 0-进行中 1-已完成 2-已过期
     */
    private Integer status;

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
