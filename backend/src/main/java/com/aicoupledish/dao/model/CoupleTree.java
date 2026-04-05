package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 情侣爱心树表
 */
@Data
@TableName("t_couple_tree")
public class CoupleTree implements Serializable {

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
     * 等级
     */
    private Integer level;

    /**
     * 总养分
     */
    private Long totalNutrient;

    /**
     * 当前等级养分
     */
    private Long currentLevelNutrient;

    /**
     * 皮肤ID
     */
    private String skinId;

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
