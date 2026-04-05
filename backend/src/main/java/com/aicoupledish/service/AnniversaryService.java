package com.aicoupledish.service;

import com.aicoupledish.domain.dto.AnniversaryDTO;
import com.aicoupledish.domain.req.AddAnniversaryReq;
import com.aicoupledish.domain.req.ReminderConfigReq;

import java.util.List;

/**
 * 纪念日服务接口
 */
public interface AnniversaryService {

    /**
     * 获取纪念日列表
     */
    List<AnniversaryDTO> getAnniversaryList(Long userId);

    /**
     * 获取即将到来的纪念日
     */
    List<AnniversaryDTO> getUpcomingAnniversaries(Long userId);

    /**
     * 获取下一个纪念日
     */
    AnniversaryDTO getNextAnniversary(Long userId);

    /**
     * 添加纪念日
     */
    Long addAnniversary(Long userId, AddAnniversaryReq req);

    /**
     * 更新纪念日
     */
    void updateAnniversary(Long userId, Long anniversaryId, AddAnniversaryReq req);

    /**
     * 删除纪念日
     */
    void deleteAnniversary(Long userId, Long anniversaryId);

    /**
     * 检查今日是否是纪念日
     */
    AnniversaryDTO checkTodayAnniversary(Long userId);

    /**
     * 更新提醒配置
     */
    void updateReminderConfig(Long userId, ReminderConfigReq req);
}