package com.aicoupledish.common.interceptor;

import com.aicoupledish.common.exception.UnauthorizedException;
import com.aicoupledish.common.utils.JwtUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * 认证拦截器 - 验证用户Token
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuthInterceptor implements HandlerInterceptor {

    private final JwtUtils jwtUtils;

    /**
     * 不需要认证的路径
     */
    private static final String[] EXCLUDE_PATHS = {
            "/user/login",
            "/user/phoneLogin",
            "/doc.html",
            "/swagger-ui",
            "/v3/api-docs",
            "/favicon.ico"
    };

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String path = request.getRequestURI();

        // 跳过不需要认证的路径（使用startsWith更精确匹配）
        for (String excludePath : EXCLUDE_PATHS) {
            if (path.startsWith(excludePath) || path.equals(excludePath)) {
                return true;
            }
        }

        String token = request.getHeader("Authorization");
        if (StringUtils.hasText(token) && token.startsWith("Bearer ")) {
            token = token.substring(7);
        }

        if (!StringUtils.hasText(token)) {
            log.warn("请求[{}]缺少Token", path);
            throw new UnauthorizedException("请先登录");
        }

        if (!jwtUtils.validateToken(token)) {
            log.warn("请求[{}]Token无效", path);
            throw new UnauthorizedException("登录已过期，请重新登录");
        }

        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            log.warn("请求[{}]无法解析用户ID", path);
            throw new UnauthorizedException("登录信息无效");
        }

        // 将用户ID存入请求属性，方便后续使用
        request.setAttribute("userId", userId);
        return true;
    }
}