package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotBlank;

/**
 * 手机号登录请求
 */
@Data
public class PhoneLoginReq {

    /**
     * 手机号
     */
    @NotBlank(message = "手机号不能为空")
    private String phone;

    /**
     * 验证码（本地开发模式下忽略）
     */
    private String verifyCode;
}
