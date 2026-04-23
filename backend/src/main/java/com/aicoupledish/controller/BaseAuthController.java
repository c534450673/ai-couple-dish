package com.aicoupledish.controller;

import com.aicoupledish.common.constants.AuthConstants;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.TokenExtractor;

import javax.servlet.http.HttpServletRequest;

/**
 * Base controller providing authenticated user ID extraction.
 */
public abstract class BaseAuthController {

    protected Long getCurrentUserId(HttpServletRequest request, JwtUtils jwtUtils) {
        Object userIdAttr = request.getAttribute(AuthConstants.USER_ID_ATTR);
        if (userIdAttr instanceof Long) {
            return (Long) userIdAttr;
        }
        if (userIdAttr instanceof Integer) {
            return ((Integer) userIdAttr).longValue();
        }

        String token = TokenExtractor.extractToken(request);
        if (token == null || token.isEmpty()) {
            throw BusinessException.USER_NOT_LOGGED_IN;
        }

        Long userId = jwtUtils.getUserIdFromToken(token);
        if (userId == null) {
            throw BusinessException.USER_NOT_LOGGED_IN;
        }
        return userId;
    }
}
