package com.aicoupledish.common.utils;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

/**
 * JWT工具类
 */
@Slf4j
@Component
public class JwtUtils {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration}")
    private Long expiration;

    @PostConstruct
    public void init() {
        if (secret == null || secret.trim().isEmpty()) {
            log.error("================================================================================");
            log.error("安全警告: JWT_SECRET 环境变量未设置!");
            log.error("请设置JWT密钥后再启动应用。生成密钥命令:");
            log.error("  openssl rand -base64 64 | tr -d '\\n'");
            log.error("================================================================================");
            throw new IllegalStateException("JWT_SECRET 环境变量必须设置");
        }
        if (secret.length() < 64) {
            log.warn("安全警告: JWT密钥长度不足64字符，建议使用更长的密钥");
        }
        log.info("JWT配置初始化完成");
    }

    /**
     * 生成Token
     */
    public String generateToken(Long userId) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", userId);
        return createToken(claims, userId.toString());
    }

    /**
     * 生成Token（带额外信息）
     */
    public String generateToken(Long userId, Map<String, Object> extraClaims) {
        Map<String, Object> claims = new HashMap<>(extraClaims);
        claims.put("userId", userId);
        return createToken(claims, userId.toString());
    }

    private String createToken(Map<String, Object> claims, String subject) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expiration);

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(subject)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(getSigningKey(), SignatureAlgorithm.HS512)
                .compact();
    }

    /**
     * 从Token获取用户ID
     */
    public Long getUserIdFromToken(String token) {
        if (token == null || token.trim().isEmpty()) {
            return null;
        }
        try {
            Claims claims = getClaimsFromToken(token);
            if (claims == null || claims.getSubject() == null) {
                return null;
            }
            return Long.parseLong(claims.getSubject());
        } catch (NumberFormatException e) {
            log.warn("Token中的用户ID格式错误: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 从Token获取数据
     */
    public Claims getClaimsFromToken(String token) {
        try {
            return Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
        } catch (JwtException e) {
            log.warn("JWT解析失败: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 验证Token是否有效
     */
    public boolean validateToken(String token) {
        try {
            Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(token);
            return true;
        } catch (JwtException e) {
            log.warn("JWT验证失败: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 判断Token是否过期
     */
    public boolean isTokenExpired(String token) {
        try {
            Claims claims = getClaimsFromToken(token);
            return claims.getExpiration().before(new Date());
        } catch (JwtException e) {
            return true;
        }
    }

    /**
     * 刷新Token
     */
    public String refreshToken(String token) {
        Claims claims = getClaimsFromToken(token);
        if (claims == null) {
            return null;
        }
        Long userId = Long.parseLong(claims.getSubject());
        return generateToken(userId);
    }

    private SecretKey getSigningKey() {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        return Keys.hmacShaKeyFor(keyBytes);
    }
}