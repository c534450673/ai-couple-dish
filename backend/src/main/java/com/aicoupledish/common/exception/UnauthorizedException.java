package com.aicoupledish.common.exception;

import lombok.Getter;

/**
 * 未授权异常 - 用户未登录或Token无效
 */
@Getter
public class UnauthorizedException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public UnauthorizedException() {
        super("未授权，请先登录");
    }

    public UnauthorizedException(String message) {
        super(message);
    }
}