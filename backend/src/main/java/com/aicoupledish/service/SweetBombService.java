package com.aicoupledish.service;

import com.aicoupledish.domain.dto.SweetBombDTO;

import java.util.List;

/**
 * 随机甜蜜炸弹服务接口
 */
public interface SweetBombService {

    /**
     * 生成并发送甜蜜炸弹
     */
    SweetBombDTO generateBomb(Long userId);

    /**
     * 获取未读炸弹列表
     */
    List<SweetBombDTO> getUnreadBombs(Long userId);

    /**
     * 获取炸弹详情
     */
    SweetBombDTO getBombDetail(Long userId, Long bombId);

    /**
     * 标记炸弹已读
     */
    void markAsRead(Long userId, Long bombId);

    /**
     * 回答炸弹问题
     */
    void answerBomb(Long userId, Long bombId, String answerContent);

    /**
     * 获取炸弹历史
     */
    List<SweetBombDTO> getBombHistory(Long userId, Integer limit);

    /**
     * 获取未读炸弹数量
     */
    Integer getUnreadCount(Long userId);
}
