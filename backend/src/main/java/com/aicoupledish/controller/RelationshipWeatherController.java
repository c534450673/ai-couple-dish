package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.RelationshipWeatherDTO;
import com.aicoupledish.service.RelationshipWeatherService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 关系气象站控制器
 */
@Api(tags = "关系气象站模块")
@RestController
@RequestMapping("/relationshipWeather")
@RequiredArgsConstructor
public class RelationshipWeatherController extends BaseAuthController {

    private final RelationshipWeatherService relationshipWeatherService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取当前天气状态")
    @GetMapping("/current")
    public Result<RelationshipWeatherDTO> getCurrentWeather() {
        Long userId = getCurrentUserId(request, jwtUtils);
        RelationshipWeatherDTO dto = relationshipWeatherService.getCurrentWeather(userId);
        return Result.success(dto);
    }

    @ApiOperation("获取互动历史")
    @GetMapping("/interactions")
    public Result<List<RelationshipWeatherDTO.InteractionRecord>> getInteractionHistory(
            @ApiParam(value = "数量限制，默认10")
            @RequestParam(required = false, defaultValue = "10") Integer limit) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<RelationshipWeatherDTO.InteractionRecord> records = relationshipWeatherService.getInteractionHistory(userId, limit);
        return Result.success(records);
    }

    @ApiOperation("获取改善建议")
    @GetMapping("/suggestions")
    public Result<List<RelationshipWeatherDTO.ImprovementSuggestion>> getSuggestions() {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<RelationshipWeatherDTO.ImprovementSuggestion> suggestions = relationshipWeatherService.getSuggestions(userId);
        return Result.success(suggestions);
    }

    @ApiOperation("获取天气预报（未来7天预测）")
    @GetMapping("/forecast")
    public Result<List<RelationshipWeatherDTO.WeatherForecast>> getWeatherForecast() {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<RelationshipWeatherDTO.WeatherForecast> forecast = relationshipWeatherService.getWeatherForecast(userId);
        return Result.success(forecast);
    }
}
