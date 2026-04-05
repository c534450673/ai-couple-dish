package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.DeepQaDTO;
import com.aicoupledish.service.DeepQaService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 情侣深度问答控制器
 */
@Api(tags = "情侣深度问答模块")
@RestController
@RequestMapping("/deepQa")
@RequiredArgsConstructor
public class DeepQaController {

    private final DeepQaService deepQaService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取当前问题")
    @GetMapping("/current")
    public Result<DeepQaDTO> getCurrentQuestion() {
        Long userId = getCurrentUserId();
        DeepQaDTO dto = deepQaService.getCurrentQuestion(userId);
        return Result.success(dto);
    }

    @ApiOperation("获取指定周的问题列表")
    @GetMapping("/week/{weekNumber}")
    public Result<List<DeepQaDTO>> getWeekQuestions(@PathVariable Integer weekNumber) {
        Long userId = getCurrentUserId();
        List<DeepQaDTO> questions = deepQaService.getWeekQuestions(userId, weekNumber);
        return Result.success(questions);
    }

    @ApiOperation("提交答案")
    @PostMapping("/submit")
    public Result<Void> submitAnswer(@RequestBody DeepQaDTO.SubmitAnswerReq req) {
        Long userId = getCurrentUserId();
        deepQaService.submitAnswer(userId, req);
        return Result.success("答案提交成功");
    }

    @ApiOperation("揭晓答案")
    @PostMapping("/reveal/{questionId}")
    public Result<DeepQaDTO> revealAnswer(@PathVariable Long questionId) {
        Long userId = getCurrentUserId();
        DeepQaDTO dto = deepQaService.revealAnswer(userId, questionId);
        return Result.success(dto);
    }

    @ApiOperation("获取进度")
    @GetMapping("/progress")
    public Result<DeepQaDTO.ProgressInfo> getProgress() {
        Long userId = getCurrentUserId();
        DeepQaDTO.ProgressInfo progress = deepQaService.getProgress(userId);
        return Result.success(progress);
    }

    @ApiOperation("获取历史问答记录")
    @GetMapping("/history")
    public Result<List<DeepQaDTO>> getHistoryAnswers(
            @ApiParam(value = "数量限制，默认20")
            @RequestParam(required = false, defaultValue = "20") Integer limit) {
        Long userId = getCurrentUserId();
        List<DeepQaDTO> history = deepQaService.getHistoryAnswers(userId, limit);
        return Result.success(history);
    }

    @ApiOperation("跳过当前问题")
    @PostMapping("/skip")
    public Result<Void> skipQuestion() {
        Long userId = getCurrentUserId();
        deepQaService.skipQuestion(userId);
        return Result.success();
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
