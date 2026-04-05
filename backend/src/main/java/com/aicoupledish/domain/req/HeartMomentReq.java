package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 创建心动时刻请求
 */
@Data
@ApiModel("创建心动时刻请求")
public class HeartMomentReq {

    @NotBlank(message = "时刻类型不能为空")
    @ApiModelProperty(value = "时刻类型：text/voice/photo", required = true)
    private String momentType;

    @ApiModelProperty("内容（文本类型必填）")
    private String content;

    @ApiModelProperty("媒体URL")
    private String mediaUrl;
}
