package com.aicoupledish.service;

import com.aicoupledish.domain.dto.DailyGreetingDTO;
import com.aicoupledish.domain.dto.GreetingStreakDTO;
import com.aicoupledish.domain.req.DailyGreetingReq;

import java.util.List;

/**
 * 每日问候服务接口
 */
public interface DailyGreetingService {

    /**
     * 发送问候
     */
    Long sendGreeting(Long userId, DailyGreetingReq req);

    /**
     * 获取今日问候状态
     */
    DailyGreetingDTO getTodayStatus(Long userId, Integer greetingType);

    /**
     * 获取问候历史记录
     */
    List<DailyGreetingDTO> getGreetingHistory(Long userId, Integer greetingType, Integer limit);

    /**
     * 获取连续打卡信息
     */
    GreetingStreakDTO getStreakInfo(Long userId, Integer streakType);

    /**
     * 获取双方打卡状态
     */
    DailyGreetingDTO getBothCheckStatus(Long userId, Integer greetingType);

    /**
     * 获取问候详情
     */
    DailyGreetingDTO getGreetingDetail(Long userId, Long greetingId);
}
