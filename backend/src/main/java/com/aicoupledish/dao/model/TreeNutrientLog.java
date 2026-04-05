package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 树养分变动日志表
 */
@Data
@TableName("t_tree_nutrient_log")
public class TreeNutrientLog implements Serializable {

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
     * 养分数量
     */
    private Integer nutrientAmount;

    /**
     * 来源行为
     */
    private String sourceAction;

    /**
     * 备注
     */
    private String remark;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
