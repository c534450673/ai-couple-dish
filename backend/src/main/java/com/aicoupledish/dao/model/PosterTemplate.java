package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 海报模板表
 */
@Data
@TableName("t_poster_template")
public class PosterTemplate implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
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
    private Integer isActive;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
