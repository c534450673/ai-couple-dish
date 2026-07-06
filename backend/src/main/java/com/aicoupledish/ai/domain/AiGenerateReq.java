package com.aicoupledish.ai.domain;

import lombok.Data;

import javax.validation.constraints.NotBlank;

@Data
public class AiGenerateReq {
    @NotBlank(message = "类型不能为空")
    private String type;
    @NotBlank(message = "描述不能为空")
    private String prompt;
}
