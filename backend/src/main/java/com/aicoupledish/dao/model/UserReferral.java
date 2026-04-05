package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 用户邀请关系表
 */
@Data
@TableName("t_user_referral")
public class UserReferral implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 邀请人ID
     */
    private Long inviterId;

    /**
     * 被邀请人ID
     */
    private Long inviteeId;

    /**
     * 邀请码
     */
    private String inviteCode;

    /**
     * 注册时间
     */
    private LocalDateTime registerTime;

    /**
     * 绑定情侣时间
     */
    private LocalDateTime bindCoupleTime;

    /**
     * 奖励状态: 0-待发放 1-已发放
     */
    private Integer rewardStatus;

    /**
     * 奖励金额
     */
    private BigDecimal rewardAmount;

    /**
     * 奖励发放时间
     */
    private LocalDateTime rewardTime;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
