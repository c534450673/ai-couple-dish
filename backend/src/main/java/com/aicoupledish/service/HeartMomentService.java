package com.aicoupledish.service;

import com.aicoupledish.domain.dto.HeartMomentDTO;
import com.aicoupledish.domain.req.HeartMomentReq;

import java.util.List;

/**
 * 心动时刻服务接口
 */
public interface HeartMomentService {

    /**
     * 创建心动时刻
     */
    Long createHeartMoment(Long userId, HeartMomentReq req);

    /**
     * 获取心动时刻列表
     */
    List<HeartMomentDTO> getHeartMomentList(Long userId, Long page, Long pageSize);

    /**
     * 删除心动时刻
     */
    void deleteHeartMoment(Long userId, Long momentId);

    /**
     * 获取随机心动时刻
     */
    HeartMomentDTO getRandomHeartMoment(Long userId);
}
