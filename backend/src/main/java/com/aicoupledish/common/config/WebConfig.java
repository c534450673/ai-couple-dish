package com.aicoupledish.common.config;

import com.aicoupledish.common.interceptor.AuthInterceptor;
import com.aicoupledish.common.interceptor.RateLimitInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web配置
 */
@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

    private final AuthInterceptor authInterceptor;
    private final RateLimitInterceptor rateLimitInterceptor;

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        // CORS配置：生产环境必须通过环境变量CORS_ORIGINS指定允许的域名
        // 多个域名用逗号分隔，例如：https://app.example.com,https://h5.example.com
        String corsOrigins = System.getenv("CORS_ORIGINS");
        if (corsOrigins == null || corsOrigins.isEmpty()) {
            // 开发环境默认允许localhost
            corsOrigins = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000";
        }

        String[] origins = corsOrigins.split(",");
        registry.addMapping("/**")
                .allowedOriginPatterns(origins)
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH")
                .allowedHeaders("*")
                .exposedHeaders("Authorization", "Content-Disposition")
                .allowCredentials(true)
                .maxAge(3600);
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // 限流拦截器（优先级高）
        registry.addInterceptor(rateLimitInterceptor)
                .addPathPatterns("/**")
                .order(0);

        // 认证拦截器
        registry.addInterceptor(authInterceptor)
                .addPathPatterns("/**")
                .excludePathPatterns(
                        "/user/login",
                        "/user/phoneLogin",
                        "/user/sendCode",
                        "/doc.html",
                        "/swagger-ui/**",
                        "/v3/api-docs/**",
                        "/webjars/**",
                        "/favicon.ico"
                )
                .order(1);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // 静态资源缓存配置
        registry.addResourceHandler("/static/**")
                .addResourceLocations("classpath:/static/")
                .setCachePeriod(31536000); // 1年缓存
    }
}