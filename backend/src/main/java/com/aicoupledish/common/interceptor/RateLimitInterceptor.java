package com.aicoupledish.common.interceptor;

import com.aicoupledish.common.annotation.RateLimit;
import com.aicoupledish.common.enums.BusinessException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.annotation.PostConstruct;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

/**
 * 限流拦截器
 * 使用Lua脚本实现原子限流
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RateLimitInterceptor implements HandlerInterceptor {

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    private static final String RATE_LIMIT_PREFIX = "rate_limit:";

    // Lua脚本：原子限流
    // 返回值：-1 表示限流，否则返回当前计数
    private static final String RATE_LIMIT_LUA_SCRIPT =
            "local current = redis.call('incr', KEYS[1]) " +
            "if current == 1 then " +
            "    redis.call('expire', KEYS[1], ARGV[1]) " +
            "end " +
            "if current > tonumber(ARGV[2]) then " +
            "    return -1 " +
            "end " +
            "return current";

    private DefaultRedisScript<Long> rateLimitScript;

    @PostConstruct
    public void init() {
        rateLimitScript = new DefaultRedisScript<>(RATE_LIMIT_LUA_SCRIPT, Long.class);
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        if (!(handler instanceof HandlerMethod)) {
            return true;
        }

        HandlerMethod handlerMethod = (HandlerMethod) handler;
        RateLimit rateLimit = handlerMethod.getMethodAnnotation(RateLimit.class);

        if (rateLimit == null) {
            return true;
        }

        String key = buildKey(request, rateLimit);
        if (key == null) {
            return true;
        }

        // 使用Lua脚本原子限流
        Long result = redisTemplate.execute(
                rateLimitScript,
                Collections.singletonList(key),
                String.valueOf(rateLimit.time()),
                String.valueOf(rateLimit.count())
        );

        if (result != null && result == -1) {
            log.warn("请求限流触发: key={}", key);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write(objectMapper.writeValueAsString(
                com.aicoupledish.common.utils.Result.error(429, rateLimit.message())
            ));
            return false;
        }

        return true;
    }

    private String buildKey(HttpServletRequest request, RateLimit rateLimit) {
        String keyPrefix = RATE_LIMIT_PREFIX;

        if (!rateLimit.key().isEmpty()) {
            keyPrefix += rateLimit.key() + ":";
        }

        switch (rateLimit.limitType()) {
            case IP:
                String ip = getClientIp(request);
                return keyPrefix + "ip:" + ip;
            case USER:
                // 从header获取用户ID
                String token = request.getHeader("Authorization");
                if (token != null && token.startsWith("Bearer ")) {
                    return keyPrefix + "user:" + token.substring(7);
                }
                return null;
            case ALL:
                return keyPrefix + "all";
            default:
                return null;
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        // 多个代理时取第一个IP
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }
}
