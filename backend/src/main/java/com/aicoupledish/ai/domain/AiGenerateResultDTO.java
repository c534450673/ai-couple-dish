package com.aicoupledish.ai.domain;

import lombok.Data;

import java.util.Map;

@Data
public class AiGenerateResultDTO {
    private String type;
    private Map<String, Object> data;
}
