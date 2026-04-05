package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.RelationshipWeatherDTO;
import com.aicoupledish.service.NotificationService;
import com.aicoupledish.service.RelationshipWeatherService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 关系气象站服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RelationshipWeatherServiceImpl implements RelationshipWeatherService {

    private final RelationshipWeatherMapper relationshipWeatherMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;
    private final DailyGreetingMapper dailyGreetingMapper;
    private final CoupleMenuMapper coupleMenuMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    /**
     * 天气等级配置
     */
    private static final List<WeatherConfig> WEATHER_CONFIGS = new ArrayList<WeatherConfig>() {{
        add(new WeatherConfig("sunny", "晴天", "☀️", "关系很好，继续保持！", 80, 100));
        add(new WeatherConfig("cloudy", "多云", "⛅", "关系稳定，可以多一些互动", 60, 79));
        add(new WeatherConfig("rainy", "小雨", "🌧️", "需要多一些关心和互动", 40, 59));
        add(new WeatherConfig("stormy", "暴风雨", "⛈️", "关系需要紧急关注！", 0, 39));
    }};

    @Override
    public RelationshipWeatherDTO getCurrentWeather(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        RelationshipWeather weather = getOrCreateWeather(user.getCoupleId());
        calculateAndUpdateWeather(user.getCoupleId());

        return buildDTO(weather);
    }

    @Override
    @Transactional
    public void updateInteractionScore(Long coupleId, Integer score, String interactionType) {
        RelationshipWeather weather = getOrCreateWeather(coupleId);

        weather.setInteractionScore(Math.min(100, Math.max(0, weather.getInteractionScore() + score)));
        weather.setDaysSinceLastInteraction(0);
        weather.setWeatherLevel(calculateWeatherLevel(weather.getInteractionScore()));

        relationshipWeatherMapper.updateById(weather);

        log.info("更新互动分数: coupleId={}, score={}, type={}", coupleId, score, interactionType);
    }

    @Override
    public List<RelationshipWeatherDTO.InteractionRecord> getInteractionHistory(Long userId, Integer limit) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<RelationshipWeatherDTO.InteractionRecord> records = new ArrayList<>();

        // 获取问候记录
        List<DailyGreeting> greetings = dailyGreetingMapper.selectList(
            new LambdaQueryWrapper<DailyGreeting>()
                    .eq(DailyGreeting::getCoupleId, user.getCoupleId())
                    .orderByDesc(DailyGreeting::getCreateTime)
                    .last("LIMIT " + (limit != null ? limit : 10))
        );

        for (DailyGreeting greeting : greetings) {
            RelationshipWeatherDTO.InteractionRecord record = new RelationshipWeatherDTO.InteractionRecord();
            record.setType("greeting");
            record.setDescription(greeting.getGreetingType() == 1 ? "早安问候" : "晚安问候");
            record.setTime(greeting.getCreateTime());
            record.setScore(5);
            records.add(record);
        }

        // 获取菜单记录
        List<CoupleMenu> menus = coupleMenuMapper.selectList(
            new LambdaQueryWrapper<CoupleMenu>()
                    .eq(CoupleMenu::getCoupleId, user.getCoupleId())
                    .isNotNull(CoupleMenu::getEatenDate)
                    .orderByDesc(CoupleMenu::getCreateTime)
                    .last("LIMIT 5")
        );

        for (CoupleMenu menu : menus) {
            RelationshipWeatherDTO.InteractionRecord record = new RelationshipWeatherDTO.InteractionRecord();
            record.setType("date");
            record.setDescription("约会: " + menu.getRestaurantName());
            record.setTime(menu.getCreateTime());
            record.setScore(10);
            records.add(record);
        }

        records.sort((a, b) -> b.getTime().compareTo(a.getTime()));

        return records;
    }

    @Override
    public List<RelationshipWeatherDTO.ImprovementSuggestion> getSuggestions(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        RelationshipWeather weather = getOrCreateWeather(user.getCoupleId());
        List<RelationshipWeatherDTO.ImprovementSuggestion> suggestions = new ArrayList<>();

        if (weather.getInteractionScore() < 80) {
            RelationshipWeatherDTO.ImprovementSuggestion suggestion = new RelationshipWeatherDTO.ImprovementSuggestion();
            suggestion.setType("interaction");
            suggestion.setTitle("增加互动");
            suggestion.setDescription("多和TA互动，提升关系温度");
            suggestion.setAction("发送一个早安或晚安问候吧");
            suggestions.add(suggestion);
        }

        if (weather.getDaysSinceLastInteraction() > 1) {
            RelationshipWeatherDTO.ImprovementSuggestion suggestion = new RelationshipWeatherDTO.ImprovementSuggestion();
            suggestion.setType("date");
            suggestion.setTitle("安排约会");
            suggestion.setDescription("已经好几天没有互动了");
            suggestion.setAction("计划一次约会吧");
            suggestions.add(suggestion);
        }

        // 添加通用建议
        if (suggestions.isEmpty()) {
            RelationshipWeatherDTO.ImprovementSuggestion suggestion = new RelationshipWeatherDTO.ImprovementSuggestion();
            suggestion.setType("maintain");
            suggestion.setTitle("继续保持");
            suggestion.setDescription("你们的关系很好，继续保持！");
            suggestion.setAction("可以尝试一个新的约会地点");
            suggestions.add(suggestion);
        }

        return suggestions;
    }

    @Override
    public List<RelationshipWeatherDTO.WeatherForecast> getWeatherForecast(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        RelationshipWeather weather = getOrCreateWeather(user.getCoupleId());
        List<RelationshipWeatherDTO.WeatherForecast> forecasts = new ArrayList<>();

        int baseScore = weather.getInteractionScore();
        LocalDate today = LocalDate.now();

        for (int i = 0; i < 7; i++) {
            RelationshipWeatherDTO.WeatherForecast forecast = new RelationshipWeatherDTO.WeatherForecast();
            forecast.setDate(today.plusDays(i).toString());

            // 简单预测：假设每天增加5分
            int predictedScore = Math.min(100, baseScore + i * 5);
            forecast.setPredictedScore(predictedScore);
            forecast.setWeatherLevel(calculateWeatherLevel(predictedScore));

            WeatherConfig config = getWeatherConfig(forecast.getWeatherLevel());
            if (config != null) {
                forecast.setWeatherIcon(config.icon);
            }

            forecasts.add(forecast);
        }

        return forecasts;
    }

    @Override
    @Transactional
    public void sendWeatherAlert(Long coupleId) {
        RelationshipWeather weather = getOrCreateWeather(coupleId);

        if (weather.getAlertSent() == 1) {
            return;
        }

        if (weather.getInteractionScore() < 40) {
            weather.setAlertSent(1);
            weather.setAlertType("low_interaction");
            relationshipWeatherMapper.updateById(weather);

            if (notificationService != null) {
                Couple couple = coupleMapper.selectById(coupleId);
                if (couple != null) {
                    String message = "你们的恋爱温度有点低了，快去和TA互动一下吧~";
                    notificationService.sendNotification(couple.getUser1Id(), 2,
                            "⛈️ 恋爱天气预警", message, null, "weather_alert");
                    notificationService.sendNotification(couple.getUser2Id(), 2,
                            "⛈️ 恋爱天气预警", message, null, "weather_alert");
                }
            }

            log.info("发送天气预警: coupleId={}", coupleId);
        }
    }

    @Override
    public String calculateWeatherLevel(Integer score) {
        if (score == null) {
            return "cloudy";
        }
        for (WeatherConfig config : WEATHER_CONFIGS) {
            if (score >= config.minScore && score <= config.maxScore) {
                return config.level;
            }
        }
        return "cloudy";
    }

    /**
     * 获取或创建天气记录
     */
    private RelationshipWeather getOrCreateWeather(Long coupleId) {
        RelationshipWeather weather = relationshipWeatherMapper.selectOne(
            new LambdaQueryWrapper<RelationshipWeather>()
                    .eq(RelationshipWeather::getCoupleId, coupleId)
                    .orderByDesc(RelationshipWeather::getCreateTime)
                    .last("LIMIT 1")
        );

        if (weather == null) {
            weather = new RelationshipWeather();
            weather.setCoupleId(coupleId);
            weather.setWeatherLevel("sunny");
            weather.setInteractionScore(60);
            weather.setDaysSinceLastInteraction(0);
            weather.setTemperatureScore(60);
            weather.setAlertSent(0);
            relationshipWeatherMapper.insert(weather);
        }

        return weather;
    }

    /**
     * 计算并更新天气
     */
    private void calculateAndUpdateWeather(Long coupleId) {
        RelationshipWeather weather = getOrCreateWeather(coupleId);

        // 计算互动分数
        LocalDate today = LocalDate.now();
        LocalDate weekAgo = today.minusDays(7);

        // 问候互动
        Long greetingCount = dailyGreetingMapper.selectCount(
            new LambdaQueryWrapper<DailyGreeting>()
                    .eq(DailyGreeting::getCoupleId, coupleId)
                    .ge(DailyGreeting::getGreetingDate, weekAgo)
        );

        // 约会互动
        Long menuCount = coupleMenuMapper.selectCount(
            new LambdaQueryWrapper<CoupleMenu>()
                    .eq(CoupleMenu::getCoupleId, coupleId)
                    .isNotNull(CoupleMenu::getEatenDate)
                    .ge(CoupleMenu::getEatenDate, weekAgo)
        );

        // 计算分数
        int score = 40; // 基础分
        if (greetingCount != null) score += greetingCount.intValue() * 3;
        if (menuCount != null) score += menuCount.intValue() * 5;
        score = Math.min(100, Math.max(0, score));

        weather.setInteractionScore(score);
        weather.setWeatherLevel(calculateWeatherLevel(score));

        // 更新距上次互动天数
        // 简化处理，实际应该查询最近的互动记录
        weather.setDaysSinceLastInteraction(0);

        relationshipWeatherMapper.updateById(weather);
    }

    private WeatherConfig getWeatherConfig(String level) {
        for (WeatherConfig config : WEATHER_CONFIGS) {
            if (config.level.equals(level)) {
                return config;
            }
        }
        return null;
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private RelationshipWeatherDTO buildDTO(RelationshipWeather weather) {
        RelationshipWeatherDTO dto = new RelationshipWeatherDTO();
        dto.setId(weather.getId());
        dto.setWeatherLevel(weather.getWeatherLevel());
        dto.setInteractionScore(weather.getInteractionScore());
        dto.setDaysSinceLastInteraction(weather.getDaysSinceLastInteraction());
        dto.setTemperatureScore(weather.getTemperatureScore());
        dto.setHasAlert(weather.getAlertSent() == 1);
        dto.setAlertType(weather.getAlertType());
        dto.setCreateTime(weather.getCreateTime());

        WeatherConfig config = getWeatherConfig(weather.getWeatherLevel());
        if (config != null) {
            dto.setWeatherLevelName(config.name);
            dto.setWeatherIcon(config.icon);
            dto.setWeatherDescription(config.description);
        }

        if (weather.getAlertSent() == 1) {
            dto.setAlertMessage("你们的关系需要一些关注，快去互动吧~");
        }

        return dto;
    }

    /**
     * 天气配置
     */
    private static class WeatherConfig {
        String level;
        String name;
        String icon;
        String description;
        int minScore;
        int maxScore;

        WeatherConfig(String level, String name, String icon, String description, int minScore, int maxScore) {
            this.level = level;
            this.name = name;
            this.icon = icon;
            this.description = description;
            this.minScore = minScore;
            this.maxScore = maxScore;
        }
    }
}
