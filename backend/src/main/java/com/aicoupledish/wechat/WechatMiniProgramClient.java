package com.aicoupledish.wechat;

import com.aicoupledish.common.enums.BusinessException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 微信小程序身份与手机号凭证交换客户端。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class WechatMiniProgramClient {

    private static final String SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session";
    private static final String ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token";
    private static final String PHONE_NUMBER_URL = "https://api.weixin.qq.com/wxa/business/getuserphonenumber";
    private static final String ACCESS_TOKEN_CACHE_KEY = "wechat:mini-program:access-token";
    private static final long ACCESS_TOKEN_REFRESH_MARGIN_SECONDS = 300;

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;
    private final RestTemplate restTemplate = createRestTemplate();

    @Value("${wechat.mini-program.app-id:}")
    private String appId;

    @Value("${wechat.mini-program.app-secret:}")
    private String appSecret;

    public LoginIdentity exchangeCodes(String loginCode, String phoneCode) {
        ensureConfigured();
        log.info("开始校验微信小程序登录凭证");

        Map<String, Object> session = request(
                "获取小程序OpenID",
                buildUri(SESSION_URL, Map.of(
                        "appid", appId,
                        "secret", appSecret,
                        "js_code", loginCode,
                        "grant_type", "authorization_code"
                )),
                HttpMethod.GET,
                null
        );
        String openid = asString(session.get("openid"));
        if (!StringUtils.hasText(openid)) {
            log.warn("微信小程序登录凭证校验失败: operation=getOpenId, providerError={}", session.get("errcode"));
            throw new BusinessException(9001, "微信登录凭证无效，请重试");
        }

        String accessToken = getAccessToken();
        Map<String, Object> phoneResponse = request(
                "换取微信手机号",
                buildUri(PHONE_NUMBER_URL, Collections.singletonMap("access_token", accessToken)),
                HttpMethod.POST,
                Collections.singletonMap("code", phoneCode)
        );
        Map<String, Object> phoneInfo = asMap(phoneResponse.get("phone_info"));
        String phone = asString(phoneInfo.get("purePhoneNumber"));
        if (!StringUtils.hasText(phone)) {
            log.warn("微信手机号凭证未返回手机号");
            throw new BusinessException(9001, "未能获取有效手机号，请重新授权");
        }

        log.info("微信小程序身份与手机号校验完成");
        return new LoginIdentity(openid, phone);
    }

    private String getAccessToken() {
        String cachedToken = redisTemplate.opsForValue().get(ACCESS_TOKEN_CACHE_KEY);
        if (StringUtils.hasText(cachedToken)) {
            return cachedToken;
        }

        Map<String, Object> response = request(
                "获取小程序AccessToken",
                buildUri(ACCESS_TOKEN_URL, Map.of(
                        "grant_type", "client_credential",
                        "appid", appId,
                        "secret", appSecret
                )),
                HttpMethod.GET,
                null
        );
        String token = asString(response.get("access_token"));
        long expiresIn = asLong(response.get("expires_in"), 0);
        if (!StringUtils.hasText(token) || expiresIn <= ACCESS_TOKEN_REFRESH_MARGIN_SECONDS) {
            log.warn("微信小程序AccessToken获取失败: providerError={}", response.get("errcode"));
            throw new BusinessException(9001, "微信登录服务暂不可用，请稍后重试");
        }

        redisTemplate.opsForValue().set(
                ACCESS_TOKEN_CACHE_KEY,
                token,
                expiresIn - ACCESS_TOKEN_REFRESH_MARGIN_SECONDS,
                TimeUnit.SECONDS
        );
        return token;
    }

    private Map<String, Object> request(String operation, URI uri, HttpMethod method, Object body) {
        HttpEntity<?> entity = HttpEntity.EMPTY;
        if (body != null) {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            entity = new HttpEntity<>(body, headers);
        }

        try {
            ResponseEntity<String> response = restTemplate.exchange(
                    uri,
                    method,
                    entity,
                    String.class
            );
            String responseBody = response.getBody();
            if (!StringUtils.hasText(responseBody)) {
                log.warn("微信接口返回空响应: operation={}", operation);
                throw new BusinessException(9001, "微信登录服务暂不可用，请稍后重试");
            }

            Map<String, Object> responseData;
            try {
                responseData = objectMapper.readValue(responseBody, new TypeReference<Map<String, Object>>() { });
            } catch (JsonProcessingException e) {
                log.error("微信接口返回无法解析的响应: operation={}, contentType={}",
                        operation, response.getHeaders().getContentType(), e);
                throw new BusinessException(9001, "微信登录服务暂不可用，请稍后重试");
            }

            Object errorCode = responseData.get("errcode");
            if (errorCode != null && !"0".equals(String.valueOf(errorCode))) {
                log.warn("微信接口返回业务错误: operation={}, providerError={}", operation, errorCode);
                throw new BusinessException(9001, "微信授权失败，请重新尝试");
            }
            return responseData;
        } catch (BusinessException e) {
            throw e;
        } catch (RestClientResponseException e) {
            log.error("微信接口请求失败: operation={}, httpStatus={}", operation, e.getRawStatusCode());
            throw new BusinessException(9001, "微信登录服务暂不可用，请稍后重试");
        } catch (RestClientException e) {
            log.error("微信接口请求失败: operation={}, errorType={}", operation, e.getClass().getSimpleName());
            throw new BusinessException(9001, "微信登录服务暂不可用，请稍后重试");
        }
    }

    private URI buildUri(String endpoint, Map<String, String> queryParameters) {
        UriComponentsBuilder builder = UriComponentsBuilder.fromHttpUrl(endpoint);
        Map<String, String> parameters = new HashMap<>(queryParameters);
        parameters.forEach(builder::queryParam);
        return builder.build().encode().toUri();
    }

    private void ensureConfigured() {
        if (!StringUtils.hasText(appId) || !StringUtils.hasText(appSecret)) {
            log.error("微信小程序登录凭据未配置: appIdPresent={}, appSecretPresent={}",
                    StringUtils.hasText(appId), StringUtils.hasText(appSecret));
            throw new BusinessException(9001, "微信登录服务暂不可用，请稍后重试");
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> asMap(Object value) {
        return value instanceof Map ? (Map<String, Object>) value : Collections.emptyMap();
    }

    private String asString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private long asLong(Object value, long defaultValue) {
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        if (value != null) {
            try {
                return Long.parseLong(String.valueOf(value));
            } catch (NumberFormatException ignored) {
                return defaultValue;
            }
        }
        return defaultValue;
    }

    private RestTemplate createRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(3000);
        factory.setReadTimeout(5000);
        return new RestTemplate(factory);
    }

    @Getter
    @RequiredArgsConstructor
    public static class LoginIdentity {
        private final String openid;
        private final String phone;
    }
}
