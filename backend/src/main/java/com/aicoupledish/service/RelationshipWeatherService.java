package com.aicoupledish.service;

import com.aicoupledish.domain.dto.RelationshipWeatherDTO;

import java.util.List;

/**
 * 关系气象站服务接口
 */
public interface RelationshipWeatherService {

    /**
     * 获取当前天气状态
     */
    RelationshipWeatherDTO getCurrentWeather(Long userId);

    /**
     * 更新互动分数
     */
    void updateInteractionScore(Long coupleId, Integer score, String interactionType);

    /**
     * 获取互动历史
     */
    List<RelationshipWeatherDTO.InteractionRecord> getInteractionHistory(Long userId, Integer limit);

    /**
     * 获取改善建议
     */
    List<RelationshipWeatherDTO.ImprovementSuggestion> getSuggestions(Long userId);

    /**
     * 获取天气预报（未来7天预测）
     */
    List<RelationshipWeatherDTO.WeatherForecast> getWeatherForecast(Long userId);

    /**
     * 发送天气预警
     */
    void sendWeatherAlert(Long coupleId);

    /**
     * 计算天气等级
     */
    String calculateWeatherLevel(Integer score);
}
