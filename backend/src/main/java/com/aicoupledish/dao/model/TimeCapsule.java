package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 时光胶囊表
 */
@Data
@TableName("t_time_capsule")
public class TimeCapsule implements Serializable {

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
     * 创建者ID
     */
    private Long creatorId;

    /**
     * 胶囊类型：text/voice/video/photo
     */
    private String capsuleType;

    /**
     * 胶囊标题
     */
    private String title;

    /**
     * 胶囊内容
     */
    private String content;

    /**
     * 媒体URLs（JSON数组）
     */
    private String mediaUrls;

    /**
     * 解锁日期
     */
    private LocalDate unlockDate;

    /**
     * 状态：0-待解锁 1-已解锁
     */
    private Integer status;

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
     * 解锁时间
     */
    private LocalDateTime unlockTime;
}
