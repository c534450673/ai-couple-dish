package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 每日任务DTO
 */
@Data
public class DailyTaskDTO {

    private Long id;

    /**
     * 任务日期
     */
    private String taskDate;

    /**
     * 任务类型
     */
    private String taskType;

    /**
     * 任务类型名称
     */
    private String taskTypeName;

    /**
     * 任务名称
     */
    private String taskName;

    /**
     * 任务描述
     */
    private String taskDescription;

    /**
     * 目标数量
     */
    private Integer targetCount;

    /**
     * 奖励养分
     */
    private Integer rewardNutrient;

    /**
     * 状态: 0-进行中 1-已完成 2-已过期
     */
    private Integer status;

    /**
     * 状态名称
     */
    private String statusName;

    /**
     * 我的进度
     */
    private TaskProgress myProgress;

    /**
     * 对方进度
     */
    private TaskProgress partnerProgress;

    /**
     * 是否已领取奖励
     */
    private Boolean rewardClaimed;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 任务进度
     */
    @Data
    public static class TaskProgress {
        private Long userId;
        private String userName;
        private String userAvatar;
        private Integer currentCount;
        private Boolean isCompleted;
        private LocalDateTime completeTime;
    }

    /**
     * 今日任务统计
     */
    @Data
    public static class TodayTaskStats {
        /**
         * 总任务数
         */
        private Integer totalTasks;

        /**
         * 已完成任务数
         */
        private Integer completedTasks;

        /**
         * 进行中任务数
         */
        private Integer inProgressTasks;

        /**
         * 总奖励养分
         */
        private Integer totalRewardNutrient;

        /**
         * 已获得养分
         */
        private Integer earnedNutrient;
    }
}
