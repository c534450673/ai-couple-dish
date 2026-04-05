package com.aicoupledish.common.aspect;

import com.aicoupledish.common.annotation.Auth;
import com.aicoupledish.common.exception.UnauthorizedException;
import com.aicoupledish.common.utils.JwtUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;
import java.lang.reflect.Method;

/**
 * AOP Aspect for handling authentication logic.
 *
 * This aspect intercepts methods annotated with {@link Auth} and validates
 * the JWT token from the request header.
 *
 * Priority: Runs before other aspects to ensure authentication is checked first.
 */
@Slf4j
@Aspect
@Component
@Order(1)
@RequiredArgsConstructor
public class AuthAspect {

    private final JwtUtils jwtUtils;

    /**
     * Paths that do not require authentication.
     */
    private static final String[] PUBLIC_PATHS = {
            "/user/login",
            "/user/phoneLogin",
            "/doc.html",
            "/swagger-ui",
            "/v3/api-docs",
            "/favicon.ico"
    };

    /**
     * Around advice for methods annotated with {@link Auth}.
     */
    @Around("@annotation(com.aicoupledish.common.annotation.Auth)")
    public Object authenticate(ProceedingJoinPoint joinPoint) throws Throwable {
        ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attributes == null) {
            log.warn("Unable to get request attributes");
            throw new UnauthorizedException("Unable to verify authentication");
        }

        HttpServletRequest request = attributes.getRequest();
        String path = request.getRequestURI();

        // Check if path is in the public paths list
        if (isPublicPath(path)) {
            return joinPoint.proceed();
        }

        // Check if the annotation requires authentication
        Auth authAnnotation = getAuthAnnotation(joinPoint);
        if (authAnnotation != null && !authAnnotation.required()) {
            return joinPoint.proceed();
        }

        // Extract and validate token
        String token = extractToken(request);

        if (!StringUtils.hasText(token)) {
            log.warn("Request [{}] missing token", path);
            throw new UnauthorizedException("Please login first");
        }

        if (!jwtUtils.validateToken(token)) {
            log.warn("Request [{}] invalid token", path);
            throw new UnauthorizedException("Login expired, please login again");
        }

        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            log.warn("Request [{}] unable to parse user ID", path);
            throw new UnauthorizedException("Invalid login information");
        }

        // Store userId in request attributes for later use
        request.setAttribute("userId", userId);

        // TODO: Add role-based access control if needed
        // Auth[] roles = authAnnotation.roles();
        // if (roles.length > 0) {
        //     checkUserRoles(userId, roles);
        // }

        log.debug("Authentication successful for user [{}] on path [{}]", userId, path);
        return joinPoint.proceed();
    }

    /**
     * Checks if the given path is a public path that doesn't require authentication.
     */
    private boolean isPublicPath(String path) {
        for (String publicPath : PUBLIC_PATHS) {
            if (path.contains(publicPath)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Extracts the JWT token from the Authorization header.
     */
    private String extractToken(HttpServletRequest request) {
        String token = request.getHeader("Authorization");
        if (StringUtils.hasText(token) && token.startsWith("Bearer ")) {
            token = token.substring(7);
        }
        return token;
    }

    /**
     * Gets the Auth annotation from the method or class.
     */
    private Auth getAuthAnnotation(ProceedingJoinPoint joinPoint) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();

        // First check method-level annotation
        Auth methodAuth = method.getAnnotation(Auth.class);
        if (methodAuth != null) {
            return methodAuth;
        }

        // Then check class-level annotation
        Class<?> targetClass = joinPoint.getTarget().getClass();
        return targetClass.getAnnotation(Auth.class);
    }
}
