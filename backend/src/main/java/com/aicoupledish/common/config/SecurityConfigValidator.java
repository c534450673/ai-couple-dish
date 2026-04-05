package com.aicoupledish.common.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.Arrays;
import java.util.regex.Pattern;

/**
 * Security configuration validator.
 *
 * This validator runs at application startup to ensure critical security
 * configurations are properly set, especially in production environments.
 */
@Slf4j
@Component
public class SecurityConfigValidator {

    /**
     * Default JWT secret that must NOT be used in production.
     */
    private static final String DEFAULT_JWT_SECRET = "aiCoupleDishSecretKey2024VeryLongAndSecureKeyThatIsAtLeast64CharactersLongForHS512Algorithm";

    /**
     * Minimum JWT secret length for HS512 algorithm.
     */
    private static final int MIN_JWT_SECRET_LENGTH = 64;

    /**
     * Known weak JWT secrets that should never be used.
     */
    private static final Pattern WEAK_JWT_PATTERN = Pattern.compile(
            "(?i)(secret|password|123456|admin|test|default|your_.*)_?(key|secret)?"
    );

    private final Environment environment;

    @Value("${jwt.secret}")
    private String jwtSecret;

    @Value("${spring.profiles.active:dev}")
    private String activeProfile;

    public SecurityConfigValidator(Environment environment) {
        this.environment = environment;
    }

    @PostConstruct
    public void validateSecurityConfig() {
        boolean isProduction = isProductionEnvironment();

        log.info("=== Security Configuration Validation ===");
        log.info("Active Profile: {}", activeProfile);
        log.info("Environment Type: {}", isProduction ? "PRODUCTION" : "NON-PRODUCTION");

        validateJwtSecret(isProduction);

        log.info("=== Security Configuration Validation Passed ===");
    }

    private boolean isProductionEnvironment() {
        return Arrays.asList(environment.getActiveProfiles()).stream()
                .anyMatch(profile -> profile.equalsIgnoreCase("prod") || profile.equalsIgnoreCase("production"));
    }

    private void validateJwtSecret(boolean isProduction) {
        boolean isUsingDefault = DEFAULT_JWT_SECRET.equals(jwtSecret);
        boolean isWeakSecret = isWeakSecret(jwtSecret);
        boolean isTooShort = jwtSecret.length() < MIN_JWT_SECRET_LENGTH;

        if (isProduction) {
            if (isUsingDefault) {
                String errorMessage = buildProductionSecurityError(
                        "JWT_SECRET is using the default value in production environment. " +
                        "This is a critical security vulnerability. " +
                        "Please set JWT_SECRET environment variable with a secure random value."
                );
                log.error(errorMessage);
                throw new SecurityException(errorMessage);
            }

            if (isWeakSecret) {
                String errorMessage = buildProductionSecurityError(
                        "JWT_SECRET appears to be a weak or guessable value in production. " +
                        "Please use a cryptographically secure random secret."
                );
                log.error(errorMessage);
                throw new SecurityException(errorMessage);
            }

            if (isTooShort) {
                String errorMessage = buildProductionSecurityError(
                        "JWT_SECRET must be at least " + MIN_JWT_SECRET_LENGTH + " characters for HS512 algorithm. " +
                        "Current length: " + jwtSecret.length()
                );
                log.error(errorMessage);
                throw new SecurityException(errorMessage);
            }

            log.info("JWT_SECRET validation passed: length={}", jwtSecret.length());
        } else {
            if (isUsingDefault) {
                log.warn("JWT_SECRET is using default value in {} environment. Consider using a secure secret in production.", activeProfile);
            } else if (isWeakSecret) {
                log.warn("JWT_SECRET appears to be weak. Consider using a cryptographically secure random value.");
            } else if (isTooShort) {
                log.warn("JWT_SECRET length is {} characters, which is below the recommended {} for production.", jwtSecret.length(), MIN_JWT_SECRET_LENGTH);
            }
        }
    }

    private boolean isWeakSecret(String secret) {
        return WEAK_JWT_PATTERN.matcher(secret).matches();
    }

    private String buildProductionSecurityError(String message) {
        return String.format(
                "\n\n===============================================\n" +
                "  SECURITY VALIDATION FAILED - PRODUCTION\n" +
                "===============================================\n" +
                "  %s\n" +
                "\n" +
                "  To fix this issue:\n" +
                "  1. Set JWT_SECRET environment variable\n" +
                "  2. Use a cryptographically secure random generator\n" +
                "  3. Ensure the secret is at least %d characters\n" +
                "  4. Example: openssl rand -base64 64\n" +
                "===============================================\n",
                message, MIN_JWT_SECRET_LENGTH
        );
    }
}
