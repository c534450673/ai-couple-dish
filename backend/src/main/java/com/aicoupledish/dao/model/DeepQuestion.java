package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 深度问答题目库表
 */
@Data
@TableName("t_deep_question")
public class DeepQuestion implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 周数
     */
    private Integer weekNumber;

    /**
     * 问题内容
     */
    private String questionText;

    /**
     * 类型: open/choice
     */
    private String questionType;

    /**
     * 选项JSON
     */
    private String options;

    /**
     * 分类: relationship/future/values/dreams
     */
    private String category;

    /**
     * 排序
     */
    private Integer sortOrder;

    /**
     * 是否启用
     */
    private Integer isActive;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
