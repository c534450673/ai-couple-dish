package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.util.Map;

/**
 * 生成海报请求
 */
@Data
@ApiModel("生成海报请求")
public class GeneratePosterReq {

    @ApiModelProperty(value = "海报类型: anniversary/loveDays/monthly/annual/custom", required = true)
    private String posterType;

    @ApiModelProperty(value = "模板ID，不传则使用默认模板")
    private Long templateId;

    @ApiModelProperty("自定义文字内容")
    private String customText;

    @ApiModelProperty("自定义图片URL")
    private String customImage;

    @ApiModelProperty("关联的纪念日ID（纪念日海报需要）")
    private Long anniversaryId;

    @ApiModelProperty("额外参数")
    private Map<String, Object> extraParams;
}
