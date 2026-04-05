package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.DailyTaskMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.mapper.UserTaskProgressMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.DailyTask;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.dao.model.UserTaskProgress;
import com.aicoupledish.domain.dto.DailyTaskDTO;
import com.aicoupledish.service.CoupleTreeService;
import com.aicoupledish.service.DailyTaskService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 每日情侣任务服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DailyTaskServiceImpl implements DailyTaskService {

    private final DailyTaskMapper dailyTaskMapper;
    private final UserTaskProgressMapper userTaskProgressMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    @Autowired(required = false)
    @Lazy
    private CoupleTreeService coupleTreeService;

    /**
     * 任务模板配置
     */
    private static final List<TaskTemplate> TASK_TEMPLATES = Arrays.asList(
        new TaskTemplate("greeting", "早安问候", "发送早安问候给TA", 1, 10),
        new TaskTemplate("goodnight", "晚安问候", "发送晚安问候给TA", 1, 10),
        new TaskTemplate("feed", "投喂TA", "给TA发送一次投喂", 1, 15),
        new TaskTemplate("menu", "添加菜单", "添加一个新的餐厅或菜品", 1, 20),
        new TaskTemplate("note", "记录美好", "写一篇美食笔记或约会日记", 1, 25),
        new TaskTemplate("wish", "许下心愿", "添加一个心愿到心愿单", 1, 15),
        new TaskTemplate("anniversary", "纪念日提醒", "查看或添加纪念日", 1, 10),
        new TaskTemplate("interaction", "互动打卡", "完成一次互动（点赞、评论等）", 3, 30)
    );

    @Override
    public List<DailyTaskDTO> getTodayTasks(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        LocalDate today = LocalDate.now();
        List<DailyTask> tasks = dailyTaskMapper.selectList(
            new LambdaQueryWrapper<DailyTask>()
                .eq(DailyTask::getCoupleId, user.getCoupleId())
                .eq(DailyTask::getTaskDate, today)
                .orderByAsc(DailyTask::getCreateTime)
        );

        // 如果今天还没有任务，生成任务
        if (tasks.isEmpty()) {
            generateDailyTasks(user.getCoupleId());
            tasks = dailyTaskMapper.selectList(
                new LambdaQueryWrapper<DailyTask>()
                    .eq(DailyTask::getCoupleId, user.getCoupleId())
                    .eq(DailyTask::getTaskDate, today)
                    .orderByAsc(DailyTask::getCreateTime)
            );
        }

        return tasks.stream().map(task -> buildDTO(task, userId)).collect(Collectors.toList());
    }

    @Override
    public DailyTaskDTO getTaskDetail(Long userId, Long taskId) {
        User user = getUserById(userId);
        DailyTask task = dailyTaskMapper.selectById(taskId);

        if (task == null) {
            throw new IllegalArgumentException("任务不存在");
        }

        if (!task.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        return buildDTO(task, userId);
    }

    @Override
    @Transactional
    public void updateProgress(Long userId, Long taskId, Integer count) {
        User user = getUserById(userId);
        DailyTask task = dailyTaskMapper.selectById(taskId);

        if (task == null) {
            throw new IllegalArgumentException("任务不存在");
        }

        if (!task.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        if (task.getStatus() == 2) {
            throw new IllegalArgumentException("任务已过期");
        }

        // 获取或创建进度记录
        UserTaskProgress progress = userTaskProgressMapper.selectOne(
            new LambdaQueryWrapper<UserTaskProgress>()
                .eq(UserTaskProgress::getTaskId, taskId)
                .eq(UserTaskProgress::getUserId, userId)
        );

        if (progress == null) {
            progress = new UserTaskProgress();
            progress.setTaskId(taskId);
            progress.setUserId(userId);
            progress.setCurrentCount(count);
            progress.setIsCompleted(0);
            userTaskProgressMapper.insert(progress);
        } else {
            progress.setCurrentCount(progress.getCurrentCount() + count);
            userTaskProgressMapper.updateById(progress);
        }

        // 检查是否完成
        if (progress.getCurrentCount() >= task.getTargetCount() && progress.getIsCompleted() == 0) {
            progress.setIsCompleted(1);
            progress.setCompleteTime(LocalDateTime.now());
            userTaskProgressMapper.updateById(progress);
        }

        // 检查双方是否都完成
        checkTaskCompletion(task);

        log.info("更新任务进度: userId={}, taskId={}, count={}", userId, taskId, count);
    }

    @Override
    @Transactional
    public void claimReward(Long userId, Long taskId) {
        User user = getUserById(userId);
        DailyTask task = dailyTaskMapper.selectById(taskId);

        if (task == null) {
            throw new IllegalArgumentException("任务不存在");
        }

        if (!task.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        if (task.getStatus() != 1) {
            throw new IllegalArgumentException("任务尚未完成");
        }

        // 检查是否已领取
        UserTaskProgress progress = userTaskProgressMapper.selectOne(
            new LambdaQueryWrapper<UserTaskProgress>()
                .eq(UserTaskProgress::getTaskId, taskId)
                .eq(UserTaskProgress::getUserId, userId)
        );

        if (progress == null || progress.getIsCompleted() != 1) {
            throw new IllegalArgumentException("请先完成任务");
        }

        // 检查是否已领取奖励
        if (progress.getIsRewardClaimed() != null && progress.getIsRewardClaimed() == 1) {
            throw new IllegalArgumentException("奖励已领取，请勿重复领取");
        }

        // 发放奖励养分
        if (coupleTreeService != null) {
            coupleTreeService.addNutrient(user.getCoupleId(), userId,
                task.getRewardNutrient(), "daily_task", "完成任务: " + task.getTaskName());
        }

        // 标记奖励已领取
        progress.setIsRewardClaimed(1);
        progress.setRewardClaimTime(LocalDateTime.now());
        userTaskProgressMapper.updateById(progress);

        log.info("领取任务奖励: userId={}, taskId={}, reward={}", userId, taskId, task.getRewardNutrient());
    }

    @Override
    public DailyTaskDTO.TodayTaskStats getTodayStats(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        LocalDate today = LocalDate.now();
        List<DailyTask> tasks = dailyTaskMapper.selectList(
            new LambdaQueryWrapper<DailyTask>()
                .eq(DailyTask::getCoupleId, user.getCoupleId())
                .eq(DailyTask::getTaskDate, today)
        );

        DailyTaskDTO.TodayTaskStats stats = new DailyTaskDTO.TodayTaskStats();
        stats.setTotalTasks(tasks.size());

        int completed = 0;
        int totalReward = 0;
        int earnedReward = 0;

        for (DailyTask task : tasks) {
            totalReward += task.getRewardNutrient();
            if (task.getStatus() == 1) {
                completed++;
                // 检查是否已领取
                UserTaskProgress progress = userTaskProgressMapper.selectOne(
                    new LambdaQueryWrapper<UserTaskProgress>()
                        .eq(UserTaskProgress::getTaskId, task.getId())
                        .eq(UserTaskProgress::getUserId, userId)
                );
                if (progress != null && progress.getIsCompleted() == 1) {
                    earnedReward += task.getRewardNutrient();
                }
            }
        }

        stats.setCompletedTasks(completed);
        stats.setInProgressTasks(tasks.size() - completed);
        stats.setTotalRewardNutrient(totalReward);
        stats.setEarnedNutrient(earnedReward);

        return stats;
    }

    @Override
    @Transactional
    public void generateDailyTasks(Long coupleId) {
        LocalDate today = LocalDate.now();

        // 检查是否已生成
        Long count = dailyTaskMapper.selectCount(
            new LambdaQueryWrapper<DailyTask>()
                .eq(DailyTask::getCoupleId, coupleId)
                .eq(DailyTask::getTaskDate, today)
        );

        if (count != null && count > 0) {
            return;
        }

        // 随机选择3-4个任务
        List<TaskTemplate> templates = new ArrayList<>(TASK_TEMPLATES);
        Collections.shuffle(templates);
        List<TaskTemplate> selectedTemplates = templates.subList(0, Math.min(4, templates.size()));

        for (TaskTemplate template : selectedTemplates) {
            DailyTask task = new DailyTask();
            task.setCoupleId(coupleId);
            task.setTaskDate(today);
            task.setTaskType(template.type);
            task.setTaskName(template.name);
            task.setTaskDescription(template.description);
            task.setTargetCount(template.targetCount);
            task.setRewardNutrient(template.rewardNutrient);
            task.setStatus(0);
            dailyTaskMapper.insert(task);
        }

        log.info("生成每日任务: coupleId={}, count={}", coupleId, selectedTemplates.size());
    }

    @Override
    @Transactional
    public void cleanExpiredTasks() {
        LocalDate today = LocalDate.now();

        List<DailyTask> expiredTasks = dailyTaskMapper.selectList(
            new LambdaQueryWrapper<DailyTask>()
                .lt(DailyTask::getTaskDate, today)
                .eq(DailyTask::getStatus, 0)
        );

        for (DailyTask task : expiredTasks) {
            task.setStatus(2);
            dailyTaskMapper.updateById(task);
        }

        log.info("清理过期任务: count={}", expiredTasks.size());
    }

    /**
     * 检查任务是否完成
     */
    private void checkTaskCompletion(DailyTask task) {
        Couple couple = coupleMapper.selectById(task.getCoupleId());
        if (couple == null) {
            return;
        }

        // 检查双方是否都完成
        UserTaskProgress progress1 = userTaskProgressMapper.selectOne(
            new LambdaQueryWrapper<UserTaskProgress>()
                .eq(UserTaskProgress::getTaskId, task.getId())
                .eq(UserTaskProgress::getUserId, couple.getUser1Id())
        );

        UserTaskProgress progress2 = userTaskProgressMapper.selectOne(
            new LambdaQueryWrapper<UserTaskProgress>()
                .eq(UserTaskProgress::getTaskId, task.getId())
                .eq(UserTaskProgress::getUserId, couple.getUser2Id())
        );

        boolean user1Completed = progress1 != null && progress1.getIsCompleted() == 1;
        boolean user2Completed = progress2 != null && progress2.getIsCompleted() == 1;

        // 如果双方都完成，更新任务状态
        if (user1Completed && user2Completed && task.getStatus() == 0) {
            task.setStatus(1);
            dailyTaskMapper.updateById(task);
            log.info("任务完成: taskId={}", task.getId());
        }
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private DailyTaskDTO buildDTO(DailyTask task, Long userId) {
        DailyTaskDTO dto = new DailyTaskDTO();
        dto.setId(task.getId());
        dto.setTaskDate(task.getTaskDate().toString());
        dto.setTaskType(task.getTaskType());
        dto.setTaskTypeName(getTaskTypeName(task.getTaskType()));
        dto.setTaskName(task.getTaskName());
        dto.setTaskDescription(task.getTaskDescription());
        dto.setTargetCount(task.getTargetCount());
        dto.setRewardNutrient(task.getRewardNutrient());
        dto.setStatus(task.getStatus());
        dto.setStatusName(getStatusName(task.getStatus()));
        dto.setCreateTime(task.getCreateTime());

        // 获取情侣信息
        Couple couple = coupleMapper.selectById(task.getCoupleId());
        if (couple != null) {
            Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();

            // 我的进度
            UserTaskProgress myProgress = userTaskProgressMapper.selectOne(
                new LambdaQueryWrapper<UserTaskProgress>()
                    .eq(UserTaskProgress::getTaskId, task.getId())
                    .eq(UserTaskProgress::getUserId, userId)
            );
            dto.setMyProgress(buildProgress(userId, myProgress));

            // 对方进度
            UserTaskProgress partnerProgress = userTaskProgressMapper.selectOne(
                new LambdaQueryWrapper<UserTaskProgress>()
                    .eq(UserTaskProgress::getTaskId, task.getId())
                    .eq(UserTaskProgress::getUserId, partnerId)
            );
            dto.setPartnerProgress(buildProgress(partnerId, partnerProgress));
        }

        return dto;
    }

    private DailyTaskDTO.TaskProgress buildProgress(Long userId, UserTaskProgress progress) {
        DailyTaskDTO.TaskProgress tp = new DailyTaskDTO.TaskProgress();
        tp.setUserId(userId);

        User user = userMapper.selectById(userId);
        if (user != null) {
            tp.setUserName(user.getNickName());
            tp.setUserAvatar(user.getAvatarUrl());
        }

        if (progress != null) {
            tp.setCurrentCount(progress.getCurrentCount());
            tp.setIsCompleted(progress.getIsCompleted() == 1);
            tp.setCompleteTime(progress.getCompleteTime());
        } else {
            tp.setCurrentCount(0);
            tp.setIsCompleted(false);
        }

        return tp;
    }

    private String getTaskTypeName(String type) {
        switch (type) {
            case "greeting": return "问候";
            case "goodnight": return "问候";
            case "feed": return "互动";
            case "menu": return "记录";
            case "note": return "记录";
            case "wish": return "心愿";
            case "anniversary": return "纪念日";
            case "interaction": return "互动";
            default: return type;
        }
    }

    private String getStatusName(Integer status) {
        switch (status) {
            case 0: return "进行中";
            case 1: return "已完成";
            case 2: return "已过期";
            default: return "未知";
        }
    }

    /**
     * 任务模板
     */
    private static class TaskTemplate {
        String type;
        String name;
        String description;
        int targetCount;
        int rewardNutrient;

        TaskTemplate(String type, String name, String description, int targetCount, int rewardNutrient) {
            this.type = type;
            this.name = name;
            this.description = description;
            this.targetCount = targetCount;
            this.rewardNutrient = rewardNutrient;
        }
    }
}
