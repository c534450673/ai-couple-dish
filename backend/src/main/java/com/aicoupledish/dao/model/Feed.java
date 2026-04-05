package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 投喂表
 */
@Data
@TableName("t_feed")
public class Feed implements Serializable {

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
     * 发送者ID
     */
    private Long senderId;

    /**
     * 接收者ID
     */
    private Long receiverId;

    /**
     * 投喂类型：meal-正餐 dessert-甜品 snack-小吃 drink-饮品
     */
    private String feedType;

    /**
     * 投喂内容描述
     */
    private String content;

    /**
     * 图片URLs（JSON数组）
     */
    private String imageUrls;

    /**
     * 留言
     */
    private String message;

    /**
     * 状态：0-待领取 1-已领取 2-已拒绝
     */
    private Integer status;

    /**
     * 过期时间
     */
    private LocalDateTime expireTime;

    /**
     * 拒绝原因
     */
    private String rejectReason;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 领取时间
     */
    private LocalDateTime receiveTime;
}