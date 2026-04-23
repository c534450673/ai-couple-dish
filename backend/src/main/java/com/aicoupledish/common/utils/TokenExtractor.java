package com.aicoupledish.common.utils;

import com.aicoupledish.common.constants.AuthConstants;

import javax.servlet.http.HttpServletRequest;

/**
 * Utility for extracting JWT tokens from HTTP requests.
 * Eliminates duplication between AuthInterceptor, AuthAspect, and BaseAuthController.
 */
public final class TokenExtractor {

    private TokenExtractor() {
        // prevent instantiation
    }

    /**
     * Extracts the JWT token from the Authorization header.
     * Strips the "Bearer " prefix if present.
     *
     * @return the raw token string, or null if absent
     */
    public static String extractToken(HttpServletRequest request) {
        String header = request.getHeader(AuthConstants.AUTH_HEADER);
        if (header != null && header.startsWith(AuthConstants.BEARER_PREFIX)) {
            return header.substring(AuthConstants.BEARER_PREFIX.length());
        }
        return header;
    }
}
