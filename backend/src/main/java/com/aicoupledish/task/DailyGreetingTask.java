package com.aicoupledish.task;

import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.DailyGreetingMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.DailyGreeting;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

/**
 * 每日问候定时任务
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DailyGreetingTask {

    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;
    private final DailyGreetingMapper dailyGreetingMapper;

    private NotificationService notificationService;

    @org.springframework.beans.factory.annotation.Autowired(required = false)
    public void setNotificationService(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    /**
     * 早安提醒 - 每天7:00
     */
    @Scheduled(cron = "0 0 7 * * ?")
    public void morningGreetingReminder() {
        log.info("开始发送早安提醒...");
        sendGreetingReminder(1, "早安", "☀️ 早安打卡提醒", "新的一天开始了，记得给TA发送早安问候哦~");
        log.info("早安提醒发送完成");
    }

    /**
     * 晚安提醒 - 每天22:00
     */
    @Scheduled(cron = "0 0 22 * * ?")
    public void nightGreetingReminder() {
        log.info("开始发送晚安提醒...");
        sendGreetingReminder(2, "晚安", "🌙 晚安打卡提醒", "夜深了，记得和TA说声晚安，做个好梦~");
        log.info("晚安提醒发送完成");
    }

    /**
     * 发送问候提醒
     */
    private void sendGreetingReminder(Integer greetingType, String greetingName, String title, String content) {
        if (notificationService == null) {
            log.warn("通知服务未初始化，跳过问候提醒");
            return;
        }

        LocalDate today = LocalDate.now();

        // 获取所有已绑定情侣关系的用户
        List<Couple> couples = coupleMapper.selectList(
            new LambdaQueryWrapper<Couple>()
                .eq(Couple::getStatus, 1)
        );

        for (Couple couple : couples) {
            try {
                // 检查用户是否已发送该类型问候
                User user1 = userMapper.selectById(couple.getUser1Id());
                User user2 = userMapper.selectById(couple.getUser2Id());

                if (user1 != null && !hasSentGreetingToday(user1.getId(), greetingType, today)) {
                    notificationService.sendNotification(user1.getId(), 1, title, content, null, "greeting_reminder");
                }

                if (user2 != null && !hasSentGreetingToday(user2.getId(), greetingType, today)) {
                    notificationService.sendNotification(user2.getId(), 1, title, content, null, "greeting_reminder");
                }
            } catch (Exception e) {
                log.error("发送问候提醒失败: coupleId={}", couple.getId(), e);
            }
        }
    }

    /**
     * 检查今日是否已发送问候
     */
    private boolean hasSentGreetingToday(Long userId, Integer greetingType, LocalDate today) {
        Long count = dailyGreetingMapper.selectCount(
            new LambdaQueryWrapper<DailyGreeting>()
                .eq(DailyGreeting::getUserId, userId)
                .eq(DailyGreeting::getGreetingType, greetingType)
                .eq(DailyGreeting::getGreetingDate, today)
        );
        return count != null && count > 0;
    }

    /**
     * 连续打卡中断提醒 - 每天23:30
     */
    @Scheduled(cron = "0 30 23 * * ?")
    public void streakBreakReminder() {
        log.info("开始检查连续打卡中断提醒...");
        if (notificationService == null) {
            log.warn("通知服务未初始化，跳过连续打卡提醒");
            return;
        }

        LocalDate today = LocalDate.now();

        // 获取所有已绑定情侣关系的用户
        List<Couple> couples = coupleMapper.selectList(
            new LambdaQueryWrapper<Couple>()
                .eq(Couple::getStatus, 1)
        );

        for (Couple couple : couples) {
            try {
                // 检查早安打卡
                checkAndSendStreakReminder(couple, 1, "早安", today);

                // 检查晚安打卡
                checkAndSendStreakReminder(couple, 2, "晚安", today);
            } catch (Exception e) {
                log.error("连续打卡中断提醒失败: coupleId={}", couple.getId(), e);
            }
        }

        log.info("连续打卡中断提醒检查完成");
    }

    /**
     * 检查并发送连续打卡中断提醒
     */
    private void checkAndSendStreakReminder(Couple couple, Integer greetingType, String greetingName, LocalDate today) {
        // 检查昨天是否双方都打卡了
        LocalDate yesterday = today.minusDays(1);

        boolean user1CheckedYesterday = hasSentGreetingToday(couple.getUser1Id(), greetingType, yesterday);
        boolean user2CheckedYesterday = hasSentGreetingToday(couple.getUser2Id(), greetingType, yesterday);

        // 如果昨天双方都打卡了，但今天还没打卡，发送提醒
        if (user1CheckedYesterday && user2CheckedYesterday) {
            User user1 = userMapper.selectById(couple.getUser1Id());
            User user2 = userMapper.selectById(couple.getUser2Id());

            boolean user1CheckedToday = hasSentGreetingToday(couple.getUser1Id(), greetingType, today);
            boolean user2CheckedToday = hasSentGreetingToday(couple.getUser2Id(), greetingType, today);

            // 如果还没到对应的打卡时间窗口，不发送提醒
            LocalTime now = LocalTime.now();
            if (greetingType == 1 && now.isBefore(LocalTime.of(7, 0))) {
                return; // 早安提醒在7点之前不发
            }
            if (greetingType == 2 && now.isBefore(LocalTime.of(21, 0))) {
                return; // 晚安提醒在21点之前不发
            }

            if (!user1CheckedToday && user1 != null) {
                notificationService.sendNotification(user1.getId(), 2,
                    "🔔 " + greetingName + "连续打卡提醒",
                    "你们已经连续打卡了，记得今天也要打卡哦，否则连续记录会中断~",
                    null, "greeting_streak");
            }

            if (!user2CheckedToday && user2 != null) {
                notificationService.sendNotification(user2.getId(), 2,
                    "🔔 " + greetingName + "连续打卡提醒",
                    "你们已经连续打卡了，记得今天也要打卡哦，否则连续记录会中断~",
                    null, "greeting_streak");
            }
        }
    }
}
