package com.aicoupledish.domain.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

/**
 * 微信手机号一键登录请求
 */
@Data
public class WechatPhoneLoginReq {

    @NotBlank(message = "loginCode不能为空")
    @Size(max = 256, message = "loginCode长度无效")
    private String loginCode;

    @NotBlank(message = "phoneCode不能为空")
    @Size(max = 256, message = "phoneCode长度无效")
    private String phoneCode;
}
