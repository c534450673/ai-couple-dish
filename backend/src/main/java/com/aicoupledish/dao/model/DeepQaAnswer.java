package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 深度问答答案表
 */
@Data
@TableName("t_deep_qa_answer")
public class DeepQaAnswer implements Serializable {

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
     * 问题ID
     */
    private Long questionId;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 答案内容
     */
    private String answerText;

    /**
     * 是否已揭晓
     */
    private Integer isRevealed;

    /**
     * 揭晓时间
     */
    private LocalDateTime revealTime;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
