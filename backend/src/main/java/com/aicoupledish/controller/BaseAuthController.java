package com.aicoupledish.controller;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.JwtUtils;

import javax.servlet.http.HttpServletRequest;

/**
 * 统一认证基类
 */
public abstract class BaseAuthController {

    protected Long getCurrentUserId(HttpServletRequest request, JwtUtils jwtUtils) {
        Object userIdAttr = request.getAttribute("userId");
        if (userIdAttr instanceof Long) {
            return (Long) userIdAttr;
        }
        if (userIdAttr instanceof Integer) {
            return ((Integer) userIdAttr).longValue();
        }

        String token = request.getHeader("Authorization");
        if (token == null || token.isEmpty()) {
            throw new BusinessException(9001, "请先登录");
        }
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }

        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            throw new BusinessException(9001, "无效的登录凭证");
        }
        return userId;
    }
}
