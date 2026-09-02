package com.aicoupledish.ai.service;

import com.aicoupledish.ai.client.KimiClient;
import com.aicoupledish.ai.config.AiProperties;
import com.aicoupledish.ai.domain.AiGenerateReq;
import com.aicoupledish.ai.domain.AiGenerateResultDTO;
import com.aicoupledish.ai.domain.AiPendingActionDTO;
import com.aicoupledish.ai.tool.AiToolDefinitions;
import com.aicoupledish.ai.tool.AiToolExecutor;
import com.aicoupledish.common.enums.BusinessException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class AiAgentService {

    private final KimiClient kimiClient;
    private final AiToolExecutor toolExecutor;
    private final AiSessionService sessionService;
    private final AiProperties aiProperties;
    private final ObjectMapper objectMapper;

    public String chatStream(Long userId, String message, String sessionId, SseEmitter emitter) throws IOException {
        String sid = sessionService.resolveSessionId(userId, sessionId);
        List<Map<String, Object>> messages = sessionService.loadMessages(userId, sid);
        messages.add(Map.of("role", "user", "content", message));

        AiPendingActionDTO pending = null;
        int rounds = 0;
        String assistantContent = null;

        while (rounds < aiProperties.getMaxToolRounds()) {
            rounds++;
            JsonNode response = kimiClient.chat(messages, AiToolDefinitions.allTools());
            JsonNode choice = response.path("choices").path(0);
            JsonNode msg = choice.path("message");

            if (msg.has("tool_calls") && msg.get("tool_calls").isArray() && msg.get("tool_calls").size() > 0) {
                Map<String, Object> assistantMsg = objectMapper.convertValue(msg, new TypeReference<>() {});
                messages.add(assistantMsg);

                for (JsonNode toolCall : msg.get("tool_calls")) {
                    String id = toolCall.path("id").asText();
                    String name = toolCall.path("function").path("name").asText();
                    String args = toolCall.path("function").path("arguments").asText();
                    AiToolExecutor.ToolResult result = toolExecutor.execute(userId, name, args);

                    if (result.pendingAction() != null) {
                        pending = result.pendingAction();
                        sessionService.savePendingAction(userId, sid, pending);
                    }

                    messages.add(Map.of(
                            "role", "tool",
                            "tool_call_id", id,
                            "content", result.content()
                    ));
                }
                continue;
            }

            JsonNode contentNode = msg.path("content");
            if (!contentNode.isMissingNode() && !contentNode.isNull()) {
                String content = contentNode.asText("");
                if (!content.isBlank()) {
                    assistantContent = content;
                }
            }
            break;
        }

        if (pending != null) {
            emitter.send(SseEmitter.event().name("pending_action").data(objectMapper.writeValueAsString(pending)));
        }

        StringBuilder fullReply = new StringBuilder();
        if (assistantContent != null) {
            fullReply.append(assistantContent);
            emitter.send(SseEmitter.event().name("token").data(assistantContent));
        } else {
            kimiClient.streamChat(messages, token -> {
                fullReply.append(token);
                try {
                    emitter.send(SseEmitter.event().name("token").data(token));
                } catch (IOException e) {
                    throw new RuntimeException(e);
                }
            });
        }

        messages.add(Map.of("role", "assistant", "content", fullReply.toString()));
        sessionService.saveMessages(userId, sid, messages);

        emitter.send(SseEmitter.event().name("session").data(sid));
        emitter.send(SseEmitter.event().name("done").data("{}"));
        emitter.complete();

        return sid;
    }

    public Map<String, Object> confirmAction(Long userId, String sessionId) {
        AiPendingActionDTO pending = sessionService.getPendingAction(userId, sessionId);
        if (pending == null) {
            throw new BusinessException(9004, "没有待确认的操作");
        }
        Long id = toolExecutor.confirmWrite(userId, pending);
        sessionService.clearPendingAction(userId, sessionId);
        Map<String, Object> result = new HashMap<>();
        result.put("actionType", pending.getActionType());
        result.put("resourceId", id);
        result.put("message", "操作已成功执行");
        return result;
    }

    public void rejectAction(Long userId, String sessionId) {
        sessionService.clearPendingAction(userId, sessionId);
    }

    public AiGenerateResultDTO generate(Long userId, AiGenerateReq req) {
        String type = req.getType().toLowerCase();
        String system = switch (type) {
            case "menu" -> """
                    你是菜单填写助手。根据用户描述生成 JSON，字段：
                    restaurantName(必填), dishName, dishCategory, price(数字), location, note, rating(1-5), status(0想去1去过2种草), eatenDate(yyyy-MM-dd)
                    只输出 JSON，不要 markdown。
                    """;
            case "recipe" -> """
                    你是菜谱填写助手。根据用户描述生成 JSON，字段：
                    title(必填), description, difficulty, cookingTime(分钟), servings,
                    ingredients: [{name, amount}], steps: [{content}], publish(false)
                    只输出 JSON，不要 markdown。
                    """;
            default -> throw new BusinessException(400, "不支持的生成类型: " + type);
        };

        List<Map<String, Object>> messages = List.of(
                Map.of("role", "system", "content", system),
                Map.of("role", "user", "content", req.getPrompt())
        );

        JsonNode response = kimiClient.generateJson(messages);
        String content = response.path("choices").path(0).path("message").path("content").asText("");
        content = content.replace("```json", "").replace("```", "").trim();

        try {
            Map<String, Object> data = objectMapper.readValue(content, new TypeReference<>() {});
            AiGenerateResultDTO dto = new AiGenerateResultDTO();
            dto.setType(type);
            dto.setData(data);
            return dto;
        } catch (Exception e) {
            log.error("Failed to parse AI generate JSON: {}", content, e);
            throw new BusinessException(9005, "AI 生成结果解析失败，请重试");
        }
    }
}
