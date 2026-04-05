package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户海报表
 */
@Data
@TableName("t_user_poster")
public class UserPoster implements Serializable {

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
     * 海报类型
     */
    private String posterType;

    /**
     * 模板ID
     */
    private Long templateId;

    /**
     * 生成的海报URL
     */
    private String posterUrl;

    /**
     * 邀请码
     */
    private String inviteCode;

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
