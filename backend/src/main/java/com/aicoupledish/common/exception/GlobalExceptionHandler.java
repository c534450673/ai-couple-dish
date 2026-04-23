package com.aicoupledish.common.exception;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

/**
 * 全局异常处理器
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    // 认证相关的错误码
    private static final int CODE_UNAUTHORIZED = 9001;
    private static final int CODE_USER_NOT_LOGGED_IN = 1003;

    /**
     * 处理未授权异常
     */
    @ExceptionHandler(UnauthorizedException.class)
    public ResponseEntity<Result<?>> handleUnauthorizedException(UnauthorizedException e) {
        log.warn("未授权异常: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Result.error(401, e.getMessage()));
    }

    /**
     * 处理业务异常
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Result<?>> handleBusinessException(BusinessException e) {
        log.warn("业务异常: {} - {}", e.getCode(), e.getMessage());

        // 认证相关错误返回 HTTP 401
        if (isAuthErrorCode(e.getCode())) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Result.error(e.getCode(), e.getMessage()));
        }

        // 参数错误返回 HTTP 400
        if (e.getCode() == 400) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Result.error(e.getCode(), e.getMessage()));
        }

        // 其他业务错误返回 HTTP 200
        return ResponseEntity.ok(Result.error(e.getCode(), e.getMessage()));
    }

    /**
     * 判断是否为认证相关错误码
     */
    private boolean isAuthErrorCode(Integer code) {
        return code != null && (code == CODE_UNAUTHORIZED || code == CODE_USER_NOT_LOGGED_IN);
    }

    /**
     * 处理参数校验异常
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Result<?>> handleValidException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        log.warn("参数校验异常: {}", message);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Result.badRequest(message));
    }

    /**
     * 处理绑定异常
     */
    @ExceptionHandler(BindException.class)
    public ResponseEntity<Result<?>> handleBindException(BindException e) {
        String message = e.getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        log.warn("绑定异常: {}", message);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Result.badRequest(message));
    }

    /**
     * 处理运行时异常
     */
    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Result<?>> handleRuntimeException(RuntimeException e) {
        log.error("运行时异常", e);
        // 不暴露具体错误信息
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Result.error("服务器内部错误，请稍后重试"));
    }

    /**
     * 处理其他异常
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Result<?>> handleException(Exception e) {
        log.error("系统异常", e);
        // 不暴露具体错误信息
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Result.error("系统错误，请稍后重试"));
    }
}