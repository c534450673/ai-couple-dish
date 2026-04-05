package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.DailyTaskDTO;
import com.aicoupledish.service.DailyTaskService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 每日情侣任务控制器
 */
@Api(tags = "每日情侣任务模块")
@RestController
@RequestMapping("/dailyTask")
@RequiredArgsConstructor
public class DailyTaskController {

    private final DailyTaskService dailyTaskService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取今日任务列表")
    @GetMapping("/today")
    public Result<List<DailyTaskDTO>> getTodayTasks() {
        Long userId = getCurrentUserId();
        List<DailyTaskDTO> tasks = dailyTaskService.getTodayTasks(userId);
        return Result.success(tasks);
    }

    @ApiOperation("获取任务详情")
    @GetMapping("/detail/{id}")
    public Result<DailyTaskDTO> getTaskDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        DailyTaskDTO dto = dailyTaskService.getTaskDetail(userId, id);
        return Result.success(dto);
    }

    @ApiOperation("更新任务进度")
    @PostMapping("/progress/{id}")
    public Result<Void> updateProgress(
            @PathVariable Long id,
            @ApiParam(value = "进度数量", required = true)
            @RequestParam Integer count) {
        Long userId = getCurrentUserId();
        dailyTaskService.updateProgress(userId, id, count);
        return Result.success();
    }

    @ApiOperation("领取任务奖励")
    @PostMapping("/claim/{id}")
    public Result<Void> claimReward(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        dailyTaskService.claimReward(userId, id);
        return Result.success();
    }

    @ApiOperation("获取今日任务统计")
    @GetMapping("/today/stats")
    public Result<DailyTaskDTO.TodayTaskStats> getTodayStats() {
        Long userId = getCurrentUserId();
        DailyTaskDTO.TodayTaskStats stats = dailyTaskService.getTodayStats(userId);
        return Result.success(stats);
    }

    private Long getCurrentUserId() {
        String token = request.getHeader("Authorization");
        if (token == null || token.isEmpty()) {
            throw new BusinessException(9001, "请先登录");
        }
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }
        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            throw new BusinessException(9001, "无效的登录凭证");
        }
        return userId;
    }
}
