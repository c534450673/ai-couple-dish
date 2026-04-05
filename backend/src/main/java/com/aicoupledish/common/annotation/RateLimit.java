package com.aicoupledish.common.annotation;

import java.lang.annotation.*;

/**
 * 接口限流注解
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RateLimit {

    /**
     * 限流key前缀
     */
    String key() default "";

    /**
     * 时间窗口（秒）
     */
    int time() default 60;

    /**
     * 限制次数
     */
    int count() default 10;

    /**
     * 限流类型：IP / USER / ALL
     */
    LimitType limitType() default LimitType.IP;

    /**
     * 限流提示消息
     */
    String message() default "请求过于频繁，请稍后再试";

    enum LimitType {
        /**
         * 按IP限流
         */
        IP,
        /**
         * 按用户限流
         */
        USER,
        /**
         * 全局限流
         */
        ALL
    }
}
