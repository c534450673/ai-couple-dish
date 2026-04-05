package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 随机甜蜜炸弹表
 */
@Data
@TableName("t_sweet_bomb")
public class SweetBomb implements Serializable {

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
     * 类型: memory/data/festival/question
     */
    private String bombType;

    /**
     * 炸弹内容JSON
     */
    private String content;

    /**
     * 发送时间
     */
    private LocalDateTime sentTime;

    /**
     * 是否已读
     */
    private Integer isRead;

    /**
     * 是否已回答
     */
    private Integer isAnswered;

    /**
     * 回答内容
     */
    private String answerContent;

    /**
     * 回答时间
     */
    private LocalDateTime answerTime;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
