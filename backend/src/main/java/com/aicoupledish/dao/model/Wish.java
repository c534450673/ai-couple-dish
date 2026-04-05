package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 心愿单表
 */
@Data
@TableName("t_wish")
public class Wish implements Serializable {

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
     * 心愿类型：restaurant-餐厅 dish-菜品 recipe-食谱
     */
    private String wishType;

    /**
     * 心愿标题
     */
    private String title;

    /**
     * 心愿描述
     */
    private String description;

    /**
     * 图片
     */
    private String imageUrl;

    /**
     * 优先级：1-低 2-中 3-高
     */
    private Integer priority;

    /**
     * 状态：0-待实现 1-进行中 2-已实现 3-已过期
     */
    private Integer status;

    /**
     * 查看者ID（TA看到过这个心愿）
     */
    private Long viewerId;

    /**
     * 查看时间
     */
    private LocalDateTime viewTime;

    /**
     * 进行中开始时间
     */
    private LocalDateTime inProgressTime;

    /**
     * 目标日期
     */
    private LocalDate targetDate;

    /**
     * 实现日期
     */
    private LocalDate achievedDate;

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