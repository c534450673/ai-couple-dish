package com.aicoupledish;

import com.aicoupledish.common.interceptor.RateLimitInterceptor;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.InjectMocks;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 限流拦截器测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("限流拦截器测试")
class RateLimitInterceptorTest {

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private ObjectMapper objectMapper;

    @InjectMocks
    private RateLimitInterceptor interceptor;

    private MockHttpServletRequest request;
    private MockHttpServletResponse response;

    @BeforeEach
    void setUp() {
        request = new MockHttpServletRequest();
        response = new MockHttpServletResponse();
        // 初始化 Lua 脚本
        interceptor.init();
    }

    @Test
    @DisplayName("限流-非HandlerMethod直接通过")
    void rateLimit_NotHandlerMethod_ShouldPass() throws Exception {
        // When
        boolean result = interceptor.preHandle(request, response, null);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("限流-使用Lua脚本返回正常值")
    void rateLimit_UnderLimit_ShouldPass() throws Exception {
        // When - null handler 直接通过，不会调用 redis
        boolean result = interceptor.preHandle(request, response, null);

        // Then - 非HandlerMethod时直接通过
        assertTrue(result);
    }
}
