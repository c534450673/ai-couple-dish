package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 打卡记录表
 */
@Data
@TableName("t_checkin_record")
public class CheckinRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 挑战ID
     */
    private Long challengeId;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 打卡日期
     */
    private LocalDate checkinDate;

    /**
     * 打卡内容
     */
    private String content;

    /**
     * 打卡图片
     */
    private String imageUrl;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
