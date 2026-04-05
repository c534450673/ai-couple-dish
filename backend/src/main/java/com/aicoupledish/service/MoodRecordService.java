package com.aicoupledish.service;

import com.aicoupledish.domain.dto.MoodRecordDTO;
import com.aicoupledish.domain.req.MoodRecordReq;

import java.util.List;

/**
 * 心情记录服务接口
 */
public interface MoodRecordService {

    /**
     * 发送心情
     */
    Long sendMood(Long userId, MoodRecordReq req);

    /**
     * 获取今日心情
     */
    List<MoodRecordDTO> getTodayMoods(Long userId);

    /**
     * 获取心情历史
     */
    List<MoodRecordDTO> getMoodHistory(Long userId, Integer limit);

    /**
     * 标记心情已读
     */
    void markAsRead(Long userId, Long moodId);

    /**
     * 获取心情统计
     */
    MoodRecordDTO.MoodStats getMoodStats(Long userId);

    /**
     * 获取可用心情类型列表
     */
    List<MoodRecordDTO.MoodType> getMoodTypes();

    /**
     * 获取未读心情数量
     */
    Integer getUnreadCount(Long userId);

    /**
     * 获取心情详情
     */
    MoodRecordDTO getMoodDetail(Long userId, Long moodId);
}
