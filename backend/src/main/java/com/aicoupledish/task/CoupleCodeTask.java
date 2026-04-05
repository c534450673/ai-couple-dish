package com.aicoupledish.task;

import com.aicoupledish.service.CoupleService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 情侣码定时任务
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class CoupleCodeTask {

    private final CoupleService coupleService;

    /**
     * 每小时检查一次情侣码过期情况，发送过期提醒
     */
    @Scheduled(cron = "0 0 * * * ?")
    public void checkExpiration() {
        log.info("开始检查情侣码过期情况...");
        try {
            coupleService.sendExpirationReminder();
            log.info("情侣码过期检查完成");
        } catch (Exception e) {
            log.error("情侣码过期检查失败", e);
        }
    }
}
