package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.MoodRecordDTO;
import com.aicoupledish.domain.req.MoodRecordReq;
import com.aicoupledish.service.MoodRecordService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 情绪投递箱控制器
 */
@Api(tags = "情绪投递箱模块")
@RestController
@RequestMapping("/mood")
@RequiredArgsConstructor
public class MoodRecordController extends BaseAuthController {

    private final MoodRecordService moodRecordService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("发送心情")
    @PostMapping("/send")
    public Result<Long> sendMood(@Valid @RequestBody MoodRecordReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        Long moodId = moodRecordService.sendMood(userId, req);
        return Result.success("心情发送成功", moodId);
    }

    @ApiOperation("获取今日心情")
    @GetMapping("/today")
    public Result<List<MoodRecordDTO>> getTodayMoods() {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<MoodRecordDTO> moods = moodRecordService.getTodayMoods(userId);
        return Result.success(moods);
    }

    @ApiOperation("获取心情历史")
    @GetMapping("/history")
    public Result<List<MoodRecordDTO>> getMoodHistory(
            @ApiParam(value = "数量限制，默认30")
            @RequestParam(required = false, defaultValue = "30") Integer limit) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<MoodRecordDTO> moods = moodRecordService.getMoodHistory(userId, limit);
        return Result.success(moods);
    }

    @ApiOperation("获取心情详情")
    @GetMapping("/detail/{id}")
    public Result<MoodRecordDTO> getMoodDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        MoodRecordDTO dto = moodRecordService.getMoodDetail(userId, id);
        return Result.success(dto);
    }

    @ApiOperation("标记心情已读")
    @PostMapping("/read/{id}")
    public Result<Void> markAsRead(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        moodRecordService.markAsRead(userId, id);
        return Result.success();
    }

    @ApiOperation("获取心情统计")
    @GetMapping("/stats")
    public Result<MoodRecordDTO.MoodStats> getMoodStats() {
        Long userId = getCurrentUserId(request, jwtUtils);
        MoodRecordDTO.MoodStats stats = moodRecordService.getMoodStats(userId);
        return Result.success(stats);
    }

    @ApiOperation("获取心情类型列表")
    @GetMapping("/types")
    public Result<List<MoodRecordDTO.MoodType>> getMoodTypes() {
        List<MoodRecordDTO.MoodType> types = moodRecordService.getMoodTypes();
        return Result.success(types);
    }

    @ApiOperation("获取未读心情数量")
    @GetMapping("/unread/count")
    public Result<Integer> getUnreadCount() {
        Long userId = getCurrentUserId(request, jwtUtils);
        Integer count = moodRecordService.getUnreadCount(userId);
        return Result.success(count);
    }
}
