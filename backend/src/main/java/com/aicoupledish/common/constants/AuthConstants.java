package com.aicoupledish.common.constants;

/**
 * Authentication-related constants.
 * Single source of truth for public paths and auth configuration.
 */
public final class AuthConstants {

    public static final String USER_ID_ATTR = "userId";
    public static final String AUTH_HEADER = "Authorization";
    public static final String BEARER_PREFIX = "Bearer ";

    /**
     * Paths that do not require authentication.
     * Used by AuthInterceptor, AuthAspect, and WebConfig.
     */
    public static final String[] PUBLIC_PATHS = {
            "/user/login",
            "/user/register",
            "/user/phoneLogin",
            "/user/sendCode",
            "/doc.html",
            "/swagger-ui",
            "/v3/api-docs",
            "/favicon.ico"
    };

    private AuthConstants() {
        // prevent instantiation
    }
}
