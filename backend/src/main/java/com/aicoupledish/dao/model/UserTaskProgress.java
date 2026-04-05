package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户任务进度表
 */
@Data
@TableName("t_user_task_progress")
public class UserTaskProgress implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 任务ID
     */
    private Long taskId;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 当前进度
     */
    private Integer currentCount;

    /**
     * 是否完成
     */
    private Integer isCompleted;

    /**
     * 完成时间
     */
    private LocalDateTime completeTime;

    /**
     * 是否已领取奖励
     */
    private Integer isRewardClaimed;

    /**
     * 奖励领取时间
     */
    private LocalDateTime rewardClaimTime;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
