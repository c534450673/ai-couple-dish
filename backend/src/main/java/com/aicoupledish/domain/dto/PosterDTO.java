package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 海报DTO
 */
@Data
public class PosterDTO {

    private Long id;

    /**
     * 海报类型
     */
    private String posterType;

    /**
     * 海报类型名称
     */
    private String posterTypeName;

    /**
     * 模板ID
     */
    private Long templateId;

    /**
     * 模板名称
     */
    private String templateName;

    /**
     * 生成的海报URL
     */
    private String posterUrl;

    /**
     * 邀请码
     */
    private String inviteCode;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 海报模板DTO
     */
    @Data
    public static class TemplateDTO {
        private Long id;
        private String templateCode;
        private String templateName;
        private String templateType;
        private String templateTypeName;
        private String templateConfig;
        private String previewUrl;
        private Boolean isActive;
    }

    /**
     * 海报生成请求
     */
    @Data
    public static class GenerateReq {
        /**
         * 海报类型: anniversary/feed/map/annual
         */
        private String posterType;

        /**
         * 模板ID
         */
        private Long templateId;

        /**
         * 关联ID（如纪念日ID、年份等）
         */
        private Long relatedId;

        /**
         * 自定义数据
         */
        private Map<String, Object> customData;
    }
}
