package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 添加心愿请求
 */
@Data
@ApiModel("添加心愿请求")
public class AddWishReq {

    @NotBlank(message = "心愿类型不能为空")
    @ApiModelProperty(value = "心愿类型", required = true)
    private String wishType;

    @NotBlank(message = "标题不能为空")
    @ApiModelProperty(value = "标题", required = true)
    private String title;

    @ApiModelProperty(value = "描述")
    private String description;

    @ApiModelProperty(value = "图片URL")
    private String imageUrl;

    @ApiModelProperty(value = "优先级")
    private Integer priority;
}
