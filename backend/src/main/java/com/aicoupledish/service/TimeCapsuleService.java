package com.aicoupledish.service;

import com.aicoupledish.domain.dto.TimeCapsuleDTO;
import com.aicoupledish.domain.req.TimeCapsuleReq;

import java.util.List;

/**
 * 时光胶囊服务接口
 */
public interface TimeCapsuleService {

    /**
     * 创建时光胶囊
     */
    Long createTimeCapsule(Long userId, TimeCapsuleReq req);

    /**
     * 获取时光胶囊列表
     */
    List<TimeCapsuleDTO> getTimeCapsuleList(Long userId);

    /**
     * 获取时光胶囊详情
     */
    TimeCapsuleDTO getTimeCapsuleDetail(Long userId, Long capsuleId);

    /**
     * 解锁时光胶囊
     */
    TimeCapsuleDTO unlockTimeCapsule(Long userId, Long capsuleId);

    /**
     * 删除时光胶囊
     */
    void deleteTimeCapsule(Long userId, Long capsuleId);

    /**
     * 获取待解锁的时光胶囊
     */
    List<TimeCapsuleDTO> getPendingTimeCapsules(Long userId);
}
