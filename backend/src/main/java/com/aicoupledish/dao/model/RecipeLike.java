package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 菜谱点赞关系表
 */
@Data
@TableName("t_recipe_like")
public class RecipeLike implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 菜谱ID
     */
    private Long recipeId;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
