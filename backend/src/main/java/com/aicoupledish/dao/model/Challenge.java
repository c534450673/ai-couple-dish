package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 打卡挑战表
 */
@Data
@TableName("t_challenge")
public class Challenge implements Serializable {

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
     * 挑战伙伴ID
     */
    private Long partnerId;

    /**
     * 挑战类型
     */
    private String challengeType;

    /**
     * 挑战标题
     */
    private String title;

    /**
     * 挑战描述
     */
    private String description;

    /**
     * 目标天数
     */
    private Integer targetDays;

    /**
     * 当前天数
     */
    private Integer currentDays;

    /**
     * 状态：0-进行中 1-已完成 2-已失败 3-已取消
     */
    private Integer status;

    /**
     * 开始日期
     */
    private LocalDate startDate;

    /**
     * 结束日期
     */
    private LocalDate endDate;

    /**
     * 奖励
     */
    private String reward;

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

    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
