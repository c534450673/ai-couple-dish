package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户海报DTO
 */
@Data
public class UserPosterDTO {

    private Long id;

    /**
     * 海报类型
     */
    private String posterType;

    /**
     * 类型名称
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
     * 分享统计
     */
    private ShareStats shareStats;

    /**
     * 分享统计
     */
    @Data
    public static class ShareStats {
        /**
         * 浏览次数
         */
        private Integer viewCount;

        /**
         * 分享次数
         */
        private Integer shareCount;

        /**
         * 通过海报注册人数
         */
        private Integer registerCount;
    }
}
