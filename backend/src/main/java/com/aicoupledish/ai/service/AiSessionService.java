package com.aicoupledish.ai.service;

import com.aicoupledish.ai.config.AiProperties;
import com.aicoupledish.ai.domain.AiPendingActionDTO;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class AiSessionService {

    private static final String MSG_PREFIX = "ai:session:msg:";
    private static final String PENDING_PREFIX = "ai:session:pending:";

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;
    private final AiProperties aiProperties;

    public String resolveSessionId(Long userId, String sessionId) {
        if (sessionId != null && !sessionId.isBlank()) {
            return sessionId;
        }
        return "u" + userId + "-" + UUID.randomUUID().toString().substring(0, 8);
    }

    public List<Map<String, Object>> loadMessages(Long userId, String sessionId) {
        String key = msgKey(userId, sessionId);
        String json = redisTemplate.opsForValue().get(key);
        if (json == null) {
            List<Map<String, Object>> list = new ArrayList<>();
            list.add(Map.of("role", "system", "content", systemPrompt()));
            return list;
        }
        try {
            return objectMapper.readValue(json, new TypeReference<>() {});
        } catch (Exception e) {
            List<Map<String, Object>> list = new ArrayList<>();
            list.add(Map.of("role", "system", "content", systemPrompt()));
            return list;
        }
    }

    public void saveMessages(Long userId, String sessionId, List<Map<String, Object>> messages) {
        trimHistory(messages);
        try {
            redisTemplate.opsForValue().set(
                    msgKey(userId, sessionId),
                    objectMapper.writeValueAsString(messages),
                    7, TimeUnit.DAYS
            );
        } catch (Exception ignored) {
            // best effort
        }
    }

    public void savePendingAction(Long userId, String sessionId, AiPendingActionDTO action) {
        try {
            redisTemplate.opsForValue().set(
                    pendingKey(userId, sessionId),
                    objectMapper.writeValueAsString(action),
                    30, TimeUnit.MINUTES
            );
        } catch (Exception ignored) {
        }
    }

    public AiPendingActionDTO getPendingAction(Long userId, String sessionId) {
        String json = redisTemplate.opsForValue().get(pendingKey(userId, sessionId));
        if (json == null) {
            return null;
        }
        try {
            return objectMapper.readValue(json, AiPendingActionDTO.class);
        } catch (Exception e) {
            return null;
        }
    }

    public void clearPendingAction(Long userId, String sessionId) {
        redisTemplate.delete(pendingKey(userId, sessionId));
    }

    private void trimHistory(List<Map<String, Object>> messages) {
        int max = aiProperties.getMaxHistory();
        if (messages.size() <= max + 1) {
            return;
        }
        Map<String, Object> system = messages.get(0);
        List<Map<String, Object>> tail = new ArrayList<>(messages.subList(messages.size() - max, messages.size()));
        List<Map<String, Object>> trimmed = new ArrayList<>();
        trimmed.add(system);
        trimmed.addAll(tail);
        messages.clear();
        messages.addAll(trimmed);
    }

    private String systemPrompt() {
        return """
                你是「情侣私密菜单」AI 助手，帮助情侣管理餐厅菜单、菜谱和情侣关系。
                规则：
                1. 语气温暖、简洁，像贴心的恋爱顾问
                2. 查询类操作通过工具直接获取数据后回答
                3. 添加菜单、创建菜谱等写操作只生成预览，提醒用户点击确认
                4. 用户未绑定情侣时，友好提示先去绑定
                5. 回答使用中文，列表清晰，避免冗长
                """;
    }

    private String msgKey(Long userId, String sessionId) {
        return MSG_PREFIX + userId + ":" + sessionId;
    }

    private String pendingKey(Long userId, String sessionId) {
        return PENDING_PREFIX + userId + ":" + sessionId;
    }
}
