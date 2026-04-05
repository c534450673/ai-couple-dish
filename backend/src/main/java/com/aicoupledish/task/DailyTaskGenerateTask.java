package com.aicoupledish.task;

import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.service.DailyTaskService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 每日任务定时任务
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DailyTaskGenerateTask {

    private final CoupleMapper coupleMapper;
    private final DailyTaskService dailyTaskService;

    /**
     * 每天凌晨0:05生成当日任务
     */
    @Scheduled(cron = "0 5 0 * * ?")
    public void generateDailyTasks() {
        log.info("开始生成每日任务...");

        // 获取所有已绑定的情侣
        List<Couple> couples = coupleMapper.selectList(
            new LambdaQueryWrapper<Couple>()
                .eq(Couple::getStatus, 1)
        );

        for (Couple couple : couples) {
            try {
                dailyTaskService.generateDailyTasks(couple.getId());
            } catch (Exception e) {
                log.error("生成每日任务失败: coupleId={}", couple.getId(), e);
            }
        }

        log.info("每日任务生成完成，共处理{}对情侣", couples.size());
    }

    /**
     * 每天凌晨0:10清理过期任务
     */
    @Scheduled(cron = "0 10 0 * * ?")
    public void cleanExpiredTasks() {
        log.info("开始清理过期任务...");
        try {
            dailyTaskService.cleanExpiredTasks();
            log.info("过期任务清理完成");
        } catch (Exception e) {
            log.error("清理过期任务失败", e);
        }
    }
}
