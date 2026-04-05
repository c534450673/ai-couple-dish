package com.aicoupledish.task;

import com.aicoupledish.common.utils.LunarCalendarUtils;
import com.aicoupledish.dao.mapper.AnniversaryMapper;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Anniversary;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;

/**
 * 纪念日提醒定时任务
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AnniversaryReminderTask {

    private final AnniversaryMapper anniversaryMapper;
    private final CoupleMapper coupleMapper;
    private final UserMapper userMapper;

    private NotificationService notificationService;

    @org.springframework.beans.factory.annotation.Autowired(required = false)
    public void setNotificationService(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    /**
     * 每天早上8点检查纪念日提醒
     */
    @Scheduled(cron = "0 0 8 * * ?")
    public void checkAnniversaryReminders() {
        log.info("开始检查纪念日提醒...");
        try {
            LocalDate today = LocalDate.now();
            LocalDate tomorrow = today.plusDays(1);

            // 获取所有开启了自动提醒的纪念日
            List<Anniversary> anniversaries = anniversaryMapper.selectList(
                new LambdaQueryWrapper<Anniversary>()
                    .eq(Anniversary::getAutoRemind, 1)
                    .eq(Anniversary::getIsDeleted, 0)
            );

            for (Anniversary anniversary : anniversaries) {
                try {
                    checkAndSendReminder(anniversary, today, tomorrow);
                } catch (Exception e) {
                    log.error("处理纪念日提醒失败: anniversaryId={}", anniversary.getId(), e);
                }
            }

            log.info("纪念日提醒检查完成");
        } catch (Exception e) {
            log.error("纪念日提醒检查失败", e);
        }
    }

    /**
     * 检查并发送纪念日提醒
     */
    private void checkAndSendReminder(Anniversary anniversary, LocalDate today, LocalDate tomorrow) {
        LocalDate nextAnniversaryDate = calculateNextAnniversaryDate(anniversary, today);
        if (nextAnniversaryDate == null) {
            return;
        }

        int daysUntil = (int) ChronoUnit.DAYS.between(today, nextAnniversaryDate);
        Integer remindDaysBefore = anniversary.getRemindDaysBefore();
        if (remindDaysBefore == null) {
            remindDaysBefore = 1; // 默认提前1天
        }

        // 检查是否需要发送提醒
        if (daysUntil < 0 || daysUntil > remindDaysBefore) {
            return;
        }

        // 检查今天是否已经发送过提醒
        if (anniversary.getLastRemindDate() != null &&
            anniversary.getLastRemindDate().equals(today)) {
            return;
        }

        // 获取情侣关系
        Couple couple = coupleMapper.selectById(anniversary.getCoupleId());
        if (couple == null || couple.getStatus() != 1) {
            return;
        }

        // 发送提醒给双方用户
        sendReminderToUsers(anniversary, couple, daysUntil, today);

        // 更新最后提醒日期
        anniversary.setLastRemindDate(today);
        anniversaryMapper.updateById(anniversary);
    }

    /**
     * 计算下一个纪念日日期
     */
    private LocalDate calculateNextAnniversaryDate(Anniversary anniversary, LocalDate today) {
        LocalDate anniversaryDate = anniversary.getAnniversaryDate();
        if (anniversaryDate == null) {
            return null;
        }

        // 如果是农历纪念日
        if (anniversary.getIsLunarDate() != null && anniversary.getIsLunarDate() == 1) {
            int lunarMonth = anniversary.getLunarMonth() != null ? anniversary.getLunarMonth() : anniversaryDate.getMonthValue();
            int lunarDay = anniversary.getLunarDay() != null ? anniversary.getLunarDay() : anniversaryDate.getDayOfMonth();

            // 获取今年农历对应的阳历日期
            LocalDate lunarDate = LunarCalendarUtils.lunarToSolar(today.getYear(), lunarMonth, lunarDay, false);
            if (lunarDate != null) {
                if (lunarDate.isBefore(today)) {
                    // 如果今年的日期已过，计算明年的
                    lunarDate = LunarCalendarUtils.lunarToSolar(today.getYear() + 1, lunarMonth, lunarDay, false);
                }
                return lunarDate;
            }
        }

        // 阳历纪念日
        LocalDate nextDate = LocalDate.of(today.getYear(), anniversaryDate.getMonth(), anniversaryDate.getDayOfMonth());
        if (nextDate.isBefore(today) || nextDate.equals(today)) {
            nextDate = LocalDate.of(today.getYear() + 1, anniversaryDate.getMonth(), anniversaryDate.getDayOfMonth());
        }
        return nextDate;
    }

    /**
     * 发送提醒给用户
     */
    private void sendReminderToUsers(Anniversary anniversary, Couple couple, int daysUntil, LocalDate today) {
        User user1 = userMapper.selectById(couple.getUser1Id());
        User user2 = userMapper.selectById(couple.getUser2Id());

        String title = daysUntil == 0 ? "🎉 今天是纪念日" : "📅 纪念日即将到来";
        String content = buildReminderContent(anniversary, daysUntil);

        String channels = anniversary.getRemindChannels();

        // 发送APP推送（检查渠道配置或单独启用标志）
        boolean shouldSendApp = (channels != null && channels.contains("app")) ||
                                (anniversary.getAppRemindEnabled() != null && anniversary.getAppRemindEnabled() == 1);
        if (shouldSendApp) {
            if (notificationService != null) {
                if (user1 != null) {
                    notificationService.sendNotification(user1.getId(), 1, title, content, anniversary.getId(), "anniversary");
                }
                if (user2 != null) {
                    notificationService.sendNotification(user2.getId(), 1, title, content, anniversary.getId(), "anniversary");
                }
            }
        }

        // 发送微信提醒（需要对接微信模板消息）
        boolean shouldSendWechat = (channels != null && channels.contains("wechat")) ||
                                    (anniversary.getWechatRemindEnabled() != null && anniversary.getWechatRemindEnabled() == 1);
        if (shouldSendWechat) {
            // TODO: 对接微信模板消息
            log.info("微信提醒: anniversary={}, daysUntil={}", anniversary.getName(), daysUntil);
        }

        // 发送短信提醒
        boolean shouldSendSms = (channels != null && channels.contains("sms")) ||
                                (anniversary.getSmsRemindEnabled() != null && anniversary.getSmsRemindEnabled() == 1);
        if (shouldSendSms) {
            // TODO: 对接短信服务
            log.info("短信提醒: anniversary={}, daysUntil={}", anniversary.getName(), daysUntil);
        }

        log.info("发送纪念日提醒: anniversary={}, daysUntil={}, channels={}",
            anniversary.getName(), daysUntil, channels);
    }

    /**
     * 构建提醒内容
     */
    private String buildReminderContent(Anniversary anniversary, int daysUntil) {
        String name = anniversary.getName();
        if (daysUntil == 0) {
            return String.format("今天是「%s」，祝你们幸福美满！", name);
        } else if (daysUntil == 1) {
            return String.format("「%s」将在明天到来，记得准备惊喜哦~", name);
        } else {
            return String.format("「%s」将在%d天后到来，提前准备起来吧~", name, daysUntil);
        }
    }
}
