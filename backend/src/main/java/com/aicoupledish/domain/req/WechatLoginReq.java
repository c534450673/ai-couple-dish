package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotBlank;

/**
 * 微信登录请求
 */
@Data
public class WechatLoginReq {

    /**
     * 微信授权code
     */
    @NotBlank(message = "code不能为空")
    private String code;

    /**
     * 昵称
     */
    private String nickName;

    /**
     * 头像URL
     */
    private String avatarUrl;
}