package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户表
 */
@Data
@TableName("t_user")
public class User implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 微信openid
     */
    private String openid;

    /**
     * 昵称
     */
    private String nickName;

    /**
     * 头像URL
     */
    private String avatarUrl;

    /**
     * 手机号
     */
    private String phone;

    /**
     * 性别：0-未知 1-男 2-女
     */
    private Integer gender;

    /**
     * 情侣ID
     */
    private Long coupleId;

    /**
     * 恋爱开始日期
     */
    private LocalDateTime loveStartDate;

    /**
     * 口味偏好（JSON格式）
     */
    private String tastePreferences;

    /**
     * 忌口（JSON格式）
     */
    private String foodRestrictions;

    /**
     * 会员等级：0-免费 1-黄金 2-铂金
     */
    private Integer memberLevel;

    /**
     * 状态：0-正常 1-禁用
     */
    private Integer status;

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

    /**
     * 是否删除：0-未删除 1-已删除
     */
    @TableLogic
    private Integer isDeleted;
}