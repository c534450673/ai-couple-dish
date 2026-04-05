package com.aicoupledish.task;

import com.aicoupledish.dao.mapper.FeedMapper;
import com.aicoupledish.dao.model.Feed;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 投喂过期处理定时任务
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class FeedExpireTask {

    private final FeedMapper feedMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    /**
     * 每10分钟检查一次过期的投喂
     */
    @Scheduled(cron = "0 */10 * * * ?")
    public void handleExpiredFeeds() {
        log.info("开始检查过期投喂...");
        try {
            LocalDateTime now = LocalDateTime.now();

            // 查询所有已过期但状态仍为待领取的投喂
            List<Feed> expiredFeeds = feedMapper.selectList(
                    new LambdaQueryWrapper<Feed>()
                            .eq(Feed::getStatus, 0) // 待领取状态
                            .lt(Feed::getExpireTime, now) // 已过期
            );

            if (expiredFeeds.isEmpty()) {
                log.info("没有过期的投喂");
                return;
            }

            int expiredCount = 0;
            for (Feed feed : expiredFeeds) {
                try {
                    // 更新状态为已过期（使用状态3表示已过期）
                    feedMapper.update(null,
                            new LambdaUpdateWrapper<Feed>()
                                    .eq(Feed::getId, feed.getId())
                                    .set(Feed::getStatus, 3) // 已过期
                    );
                    expiredCount++;

                    // 发送通知给发送者
                    if (notificationService != null) {
                        notificationService.sendNotification(
                                feed.getSenderId(),
                                2,
                                "⏰ 投喂已过期",
                                "您发送的投喂已过期未被领取，下次记得提醒TA及时领取哦！",
                                feed.getId(),
                                "feed"
                        );
                    }
                } catch (Exception e) {
                    log.error("处理过期投喂失败: feedId={}", feed.getId(), e);
                }
            }

            log.info("过期投喂处理完成，共处理 {} 条", expiredCount);
        } catch (Exception e) {
            log.error("过期投喂检查失败", e);
        }
    }
}
