package com.aicoupledish.ai.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Kimi / OpenAI 兼容 AI 网关配置（密钥仅通过环境变量注入）
 */
@Data
@ConfigurationProperties(prefix = "ai")
public class AiProperties {

    private String baseUrl = "";
    private String apiKey = "";
    private String model = "kimi-k2.6";
    private int timeoutMs = 120000;
    private int maxHistory = 20;
    private int maxToolRounds = 5;

    public boolean isConfigured() {
        return baseUrl != null && !baseUrl.isBlank()
                && apiKey != null && !apiKey.isBlank();
    }
}
