package com.aicoupledish.ai.client;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import com.aicoupledish.ai.config.AiProperties;
import com.aicoupledish.common.enums.BusinessException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/**
 * OpenAI 兼容 Chat Completions 客户端（支持流式 SSE）
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class KimiClient {

    private final AiProperties aiProperties;
    private final ObjectMapper objectMapper;

    public JsonNode chat(List<Map<String, Object>> messages, List<Map<String, Object>> tools) {
        ensureConfigured();
        ObjectNode body = buildBody(messages, tools, false);
        String url = normalizeUrl() + "/chat/completions";
        try {
            HttpResponse response = HttpRequest.post(url)
                    .header("Authorization", "Bearer " + aiProperties.getApiKey())
                    .header("Content-Type", "application/json")
                    .timeout(aiProperties.getTimeoutMs())
                    .body(body.toString())
                    .execute();
            if (!response.isOk()) {
                log.error("Kimi API error: status={}, body={}", response.getStatus(), response.body());
                throw new BusinessException(9001, "AI 服务暂时不可用，请稍后再试");
            }
            return objectMapper.readTree(response.body());
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("Kimi API call failed", e);
            throw new BusinessException(9001, "AI 服务调用失败：" + e.getMessage());
        }
    }

    public void streamChat(List<Map<String, Object>> messages, Consumer<String> onToken) {
        ensureConfigured();
        ObjectNode body = buildBody(messages, null, true);
        String url = normalizeUrl() + "/chat/completions";
        try {
            HttpResponse response = HttpRequest.post(url)
                    .header("Authorization", "Bearer " + aiProperties.getApiKey())
                    .header("Content-Type", "application/json")
                    .header("Accept", "text/event-stream")
                    .timeout(aiProperties.getTimeoutMs())
                    .body(body.toString())
                    .execute();

            if (!response.isOk()) {
                log.error("Kimi stream error: status={}, body={}", response.getStatus(), response.body());
                throw new BusinessException(9001, "AI 服务暂时不可用，请稍后再试");
            }

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(response.bodyStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (!line.startsWith("data:")) {
                        continue;
                    }
                    String data = line.substring(5).trim();
                    if ("[DONE]".equals(data)) {
                        break;
                    }
                    JsonNode chunk = objectMapper.readTree(data);
                    JsonNode delta = chunk.path("choices").path(0).path("delta");
                    if (delta.has("content") && !delta.get("content").isNull()) {
                        onToken.accept(delta.get("content").asText());
                    }
                }
            }
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("Kimi stream failed", e);
            throw new BusinessException(9001, "AI 流式响应失败：" + e.getMessage());
        }
    }

    public JsonNode generateJson(List<Map<String, Object>> messages) {
        return chat(messages, null);
    }

    private ObjectNode buildBody(List<Map<String, Object>> messages,
                                 List<Map<String, Object>> tools,
                                 boolean stream) {
        ObjectNode body = objectMapper.createObjectNode();
        body.put("model", aiProperties.getModel());
        body.put("stream", stream);
        ArrayNode msgArray = body.putArray("messages");
        for (Map<String, Object> msg : messages) {
            msgArray.add(objectMapper.valueToTree(msg));
        }
        if (tools != null && !tools.isEmpty()) {
            ArrayNode toolsArray = body.putArray("tools");
            for (Map<String, Object> tool : tools) {
                toolsArray.add(objectMapper.valueToTree(tool));
            }
            body.put("tool_choice", "auto");
        }
        return body;
    }

    private void ensureConfigured() {
        if (!aiProperties.isConfigured()) {
            throw new BusinessException(9002, "AI 服务未配置，请设置 AI_BASE_URL 和 AI_API_KEY 环境变量");
        }
    }

    private String normalizeUrl() {
        String base = aiProperties.getBaseUrl().trim();
        if (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        return base;
    }
}
