package com.aicoupledish.domain.dto;

import lombok.Data;

/**
 * 海报模板DTO
 */
@Data
public class PosterTemplateDTO {

    private Long id;

    /**
     * 模板编码
     */
    private String templateCode;

    /**
     * 模板名称
     */
    private String templateName;

    /**
     * 类型: anniversary/feed/map/annual
     */
    private String templateType;

    /**
     * 类型名称
     */
    private String templateTypeName;

    /**
     * 模板配置JSON
     */
    private String templateConfig;

    /**
     * 预览图URL
     */
    private String previewUrl;

    /**
     * 是否启用
     */
    private Boolean isActive;
}
