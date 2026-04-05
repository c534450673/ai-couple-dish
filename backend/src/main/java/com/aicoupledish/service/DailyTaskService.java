package com.aicoupledish.service;

import com.aicoupledish.domain.dto.DailyTaskDTO;

import java.util.List;

/**
 * 每日情侣任务服务接口
 */
public interface DailyTaskService {

    /**
     * 获取今日任务列表
     */
    List<DailyTaskDTO> getTodayTasks(Long userId);

    /**
     * 获取任务详情
     */
    DailyTaskDTO getTaskDetail(Long userId, Long taskId);

    /**
     * 更新任务进度
     */
    void updateProgress(Long userId, Long taskId, Integer count);

    /**
     * 领取任务奖励
     */
    void claimReward(Long userId, Long taskId);

    /**
     * 获取今日任务统计
     */
    DailyTaskDTO.TodayTaskStats getTodayStats(Long userId);

    /**
     * 生成每日任务（定时任务调用）
     */
    void generateDailyTasks(Long coupleId);

    /**
     * 清理过期任务（定时任务调用）
     */
    void cleanExpiredTasks();
}
