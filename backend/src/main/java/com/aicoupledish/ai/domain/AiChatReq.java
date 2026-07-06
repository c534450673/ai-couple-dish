package com.aicoupledish.ai.domain;

import lombok.Data;

import javax.validation.constraints.NotBlank;

@Data
public class AiChatReq {
    @NotBlank(message = "消息不能为空")
    private String message;
    private String sessionId;
}
