package com.aicoupledish.ai.controller;

import com.aicoupledish.ai.domain.AiChatReq;
import com.aicoupledish.ai.domain.AiConfirmReq;
import com.aicoupledish.ai.domain.AiGenerateReq;
import com.aicoupledish.ai.domain.AiGenerateResultDTO;
import com.aicoupledish.ai.service.AiAgentService;
import com.aicoupledish.common.annotation.RateLimit;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.controller.BaseAuthController;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.Map;

@Slf4j
@Api(tags = "AI 助手")
@RestController
@RequestMapping("/ai")
@RequiredArgsConstructor
public class AiChatController extends BaseAuthController {

    private final AiAgentService aiAgentService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("流式聊天（SSE）")
    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @RateLimit(key = "aiChat", time = 60, count = 30, limitType = RateLimit.LimitType.USER, message = "AI 请求太频繁，请稍后再试")
    public SseEmitter chatStream(@Valid @RequestBody AiChatReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        SseEmitter emitter = new SseEmitter(180000L);
        emitter.onTimeout(emitter::complete);
        emitter.onError(e -> log.warn("SSE error userId={}", userId, e));

        new Thread(() -> {
            try {
                aiAgentService.chatStream(userId, req.getMessage(), req.getSessionId(), emitter);
            } catch (Exception e) {
                log.error("AI chat stream failed", e);
                try {
                    emitter.send(SseEmitter.event().name("error").data(e.getMessage()));
                } catch (Exception ignored) {
                }
                emitter.completeWithError(e);
            }
        }).start();

        return emitter;
    }

    @ApiOperation("确认待执行操作")
    @PostMapping("/chat/confirm")
    @RateLimit(key = "aiConfirm", time = 60, count = 20, limitType = RateLimit.LimitType.USER)
    public Result<Map<String, Object>> confirm(@RequestBody AiConfirmReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        return Result.success(aiAgentService.confirmAction(userId, req.getSessionId()));
    }

    @ApiOperation("取消待执行操作")
    @PostMapping("/chat/reject")
    public Result<Void> reject(@RequestBody AiConfirmReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        aiAgentService.rejectAction(userId, req.getSessionId());
        return Result.success("已取消");
    }

    @ApiOperation("AI 帮填（菜单/菜谱表单）")
    @PostMapping("/generate")
    @RateLimit(key = "aiGenerate", time = 60, count = 20, limitType = RateLimit.LimitType.USER)
    public Result<AiGenerateResultDTO> generate(@Valid @RequestBody AiGenerateReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        return Result.success(aiAgentService.generate(userId, req));
    }
}
