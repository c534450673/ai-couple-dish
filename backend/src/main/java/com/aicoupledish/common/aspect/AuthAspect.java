package com.aicoupledish.common.aspect;

import com.aicoupledish.common.annotation.Auth;
import com.aicoupledish.common.constants.AuthConstants;
import com.aicoupledish.common.exception.UnauthorizedException;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.TokenExtractor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.core.annotation.Order;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;
import java.lang.reflect.Method;
import java.util.concurrent.TimeUnit;

/**
 * AOP Aspect for handling authentication logic.
 * Intercepts methods annotated with {@link Auth} and validates JWT tokens.
 */
@Slf4j
@Aspect
@Component
@Order(1)
@RequiredArgsConstructor
public class AuthAspect {

    private final JwtUtils jwtUtils;
    private final RedisTemplate<String, String> redisTemplate;

    private static final String LOGOUT_BLACKLIST_PREFIX = "logout:blacklist:";

    @Around("@annotation(com.aicoupledish.common.annotation.Auth)")
    public Object authenticate(ProceedingJoinPoint joinPoint) throws Throwable {
        ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attributes == null) {
            log.warn("Unable to get request attributes");
            throw new UnauthorizedException("Unable to verify authentication");
        }

        HttpServletRequest request = attributes.getRequest();
        String path = request.getRequestURI();

        if (isPublicPath(path)) {
            return joinPoint.proceed();
        }

        Auth authAnnotation = getAuthAnnotation(joinPoint);
        if (authAnnotation != null && !authAnnotation.required()) {
            return joinPoint.proceed();
        }

        String token = TokenExtractor.extractToken(request);

        if (!StringUtils.hasText(token)) {
            log.warn("Request [{}] missing token", path);
            throw new UnauthorizedException("Please login first");
        }

        if (!jwtUtils.validateToken(token)) {
            log.warn("Request [{}] invalid token", path);
            throw new UnauthorizedException("Login expired, please login again");
        }

        // Check if token is blacklisted (user logged out)
        String jti = jwtUtils.getJtiFromToken(token);
        if (jti != null && Boolean.TRUE.equals(redisTemplate.hasKey(LOGOUT_BLACKLIST_PREFIX + jti))) {
            log.warn("Request [{}] token is blacklisted", path);
            throw new UnauthorizedException("Login expired, please login again");
        }

        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            log.warn("Request [{}] unable to parse user ID", path);
            throw new UnauthorizedException("Invalid login information");
        }

        request.setAttribute(AuthConstants.USER_ID_ATTR, userId);

        log.debug("Authentication successful for user [{}] on path [{}]", userId, path);
        return joinPoint.proceed();
    }

    private boolean isPublicPath(String path) {
        for (String publicPath : AuthConstants.PUBLIC_PATHS) {
            if (path.startsWith(publicPath) || path.equals(publicPath)) {
                return true;
            }
        }
        return false;
    }

    private Auth getAuthAnnotation(ProceedingJoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();

        Auth methodAuth = method.getAnnotation(Auth.class);
        if (methodAuth != null) {
            return methodAuth;
        }

        Class<?> targetClass = joinPoint.getTarget().getClass();
        return targetClass.getAnnotation(Auth.class);
    }
}
