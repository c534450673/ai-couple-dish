package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotNull;

/**
 * 生成情侣码请求
 */
@Data
public class GenerateCodeReq {

    /**
     * 恋爱开始日期
     */
    @NotNull(message = "恋爱开始日期不能为空")
    private String loveStartDate;
}