package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 情侣关系表
 */
@Data
@TableName("t_couple")
public class Couple implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 情侣码
     */
    private String coupleCode;

    /**
     * 用户1ID（发起方）
     */
    @TableField("user_1_id")
    private Long user1Id;

    /**
     * 用户2ID（确认方）
     */
    @TableField("user_2_id")
    private Long user2Id;

    /**
     * 恋爱开始日期
     */
    private LocalDate startDate;

    /**
     * 恋爱天数
     */
    private Integer loveDays;

    /**
     * 情侣昵称（如"小明&小红"）
     */
    private String coupleNickname;

    /**
     * 状态：0-待确认 1-已绑定 2-已解除 3-申请解绑中
     */
    private Integer status;

    /**
     * 解绑申请者ID
     */
    private Long unbindApplicantId;

    /**
     * 解绑申请时间
     */
    @TableField("unbind_time")
    private LocalDateTime unbindApplyTime;

    /**
     * 头像框样式
     */
    private String avatarFrame;

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