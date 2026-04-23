package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.DailyGreetingDTO;
import com.aicoupledish.domain.dto.GreetingStreakDTO;
import com.aicoupledish.domain.req.DailyGreetingReq;
import com.aicoupledish.service.DailyGreetingService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 每日问候控制器
 */
@Api(tags = "早安晚安心动打卡模块")
@RestController
@RequestMapping("/dailyGreeting")
@RequiredArgsConstructor
public class DailyGreetingController extends BaseAuthController {

    private final DailyGreetingService dailyGreetingService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("发送问候")
    @PostMapping("/send")
    public Result<Long> sendGreeting(@Valid @RequestBody DailyGreetingReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        Long greetingId = dailyGreetingService.sendGreeting(userId, req);
        return Result.success("问候发送成功", greetingId);
    }

    @ApiOperation("获取今日问候状态")
    @GetMapping("/today/status")
    public Result<DailyGreetingDTO> getTodayStatus(
            @ApiParam(value = "问候类型: 1-早安 2-晚安", required = true)
            @RequestParam Integer greetingType) {
        Long userId = getCurrentUserId(request, jwtUtils);
        DailyGreetingDTO dto = dailyGreetingService.getTodayStatus(userId, greetingType);
        return Result.success(dto);
    }

    @ApiOperation("获取双方打卡状态")
    @GetMapping("/both/status")
    public Result<DailyGreetingDTO> getBothCheckStatus(
            @ApiParam(value = "问候类型: 1-早安 2-晚安", required = true)
            @RequestParam Integer greetingType) {
        Long userId = getCurrentUserId(request, jwtUtils);
        DailyGreetingDTO dto = dailyGreetingService.getBothCheckStatus(userId, greetingType);
        return Result.success(dto);
    }

    @ApiOperation("获取连续打卡信息")
    @GetMapping("/streak")
    public Result<GreetingStreakDTO> getStreakInfo(
            @ApiParam(value = "类型: 1-早安连续 2-晚安连续", required = true)
            @RequestParam Integer streakType) {
        Long userId = getCurrentUserId(request, jwtUtils);
        GreetingStreakDTO dto = dailyGreetingService.getStreakInfo(userId, streakType);
        return Result.success(dto);
    }

    @ApiOperation("获取问候历史记录")
    @GetMapping("/history")
    public Result<List<DailyGreetingDTO>> getGreetingHistory(
            @ApiParam(value = "问候类型: 1-早安 2-晚安，不传则查询全部")
            @RequestParam(required = false) Integer greetingType,
            @ApiParam(value = "数量限制，默认30")
            @RequestParam(required = false, defaultValue = "30") Integer limit) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<DailyGreetingDTO> list = dailyGreetingService.getGreetingHistory(userId, greetingType, limit);
        return Result.success(list);
    }

    @ApiOperation("获取问候详情")
    @GetMapping("/detail/{id}")
    public Result<DailyGreetingDTO> getGreetingDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        DailyGreetingDTO dto = dailyGreetingService.getGreetingDetail(userId, id);
        return Result.success(dto);
    }
}
