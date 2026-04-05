package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 菜谱表
 */
@Data
@TableName("t_recipe")
public class Recipe implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 菜谱标题
     */
    private String title;

    /**
     * 封面URL
     */
    private String coverUrl;

    /**
     * 菜谱描述
     */
    private String description;

    /**
     * 食材（JSON数组）
     */
    private String ingredients;

    /**
     * 制作步骤（JSON数组）
     */
    private String steps;

    /**
     * 难度：easy/medium/hard
     */
    private String difficulty;

    /**
     * 烹饪时间（分钟）
     */
    private Integer cookingTime;

    /**
     * 份量
     */
    private Integer servings;

    /**
     * 状态：0-草稿 1-已发布
     */
    private Integer status;

    /**
     * 点赞数
     */
    private Integer likeCount;

    /**
     * 收藏数
     */
    private Integer collectCount;

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
