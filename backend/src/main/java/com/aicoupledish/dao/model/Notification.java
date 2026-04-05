package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 通知表
 */
@Data
@TableName("t_notification")
public class Notification implements Serializable {

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
     * 通知类型：1-系统通知 2-互动通知 3-提醒通知
     */
    private Integer type;

    /**
     * 通知标题
     */
    private String title;

    /**
     * 通知内容
     */
    private String content;

    /**
     * 关联ID（如菜单ID、笔记ID等）
     */
    private Long relatedId;

    /**
     * 关联类型（如menu、note、feed等）
     */
    private String relatedType;

    /**
     * 发送者ID（用于互动通知）
     */
    private Long senderId;

    /**
     * 是否已读：0-未读 1-已读
     */
    private Integer isRead;

    /**
     * 阅读时间
     */
    private LocalDateTime readTime;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}