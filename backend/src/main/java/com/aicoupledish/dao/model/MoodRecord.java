package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 心情记录表
 */
@Data
@TableName("t_mood_record")
public class MoodRecord implements Serializable {

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
     * 情侣ID
     */
    private Long coupleId;

    /**
     * 心情类型: happy/tired/upset/miss_you/love/sad/angry/anxious
     */
    private String moodType;

    /**
     * 心情描述
     */
    private String description;

    /**
     * 心情图标
     */
    private String moodIcon;

    /**
     * 心情颜色
     */
    private String moodColor;

    /**
     * 记录日期
     */
    private LocalDate recordDate;

    /**
     * 是否已读
     */
    private Integer isRead;

    /**
     * 阅读时间
     */
    private LocalDateTime readTime;

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
