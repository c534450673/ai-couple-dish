package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotBlank;

/**
 * 绑定情侣请求
 */
@Data
public class BindCoupleReq {

    /**
     * 情侣码
     */
    @NotBlank(message = "情侣码不能为空")
    private String coupleCode;
}