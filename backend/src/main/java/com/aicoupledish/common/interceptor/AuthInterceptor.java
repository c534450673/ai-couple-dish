package com.aicoupledish.common.interceptor;

import com.aicoupledish.common.constants.AuthConstants;
import com.aicoupledish.common.exception.UnauthorizedException;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.TokenExtractor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * Authentication interceptor - validates user JWT tokens.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuthInterceptor implements HandlerInterceptor {

    private final JwtUtils jwtUtils;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String path = request.getRequestURI();

        if (isPublicPath(path)) {
            return true;
        }

        String token = TokenExtractor.extractToken(request);

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

        request.setAttribute(AuthConstants.USER_ID_ATTR, userId);
        return true;
    }

    private boolean isPublicPath(String path) {
        for (String publicPath : AuthConstants.PUBLIC_PATHS) {
            if (path.startsWith(publicPath) || path.equals(publicPath)) {
                return true;
            }
        }
        return false;
    }
}
