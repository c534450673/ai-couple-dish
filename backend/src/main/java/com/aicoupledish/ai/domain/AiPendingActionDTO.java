package com.aicoupledish.ai.domain;

import lombok.Data;

import java.util.Map;

@Data
public class AiPendingActionDTO {
    private String actionId;
    private String actionType;
    private String title;
    private String summary;
    private Map<String, Object> payload;
}
