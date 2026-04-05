package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

/**
 * 浇水请求
 */
@Data
@ApiModel("浇水请求")
public class WaterTreeReq {

    @ApiModelProperty("养分数量")
    private Integer nutrientAmount;

    @ApiModelProperty("来源行为")
    private String sourceAction;

    @ApiModelProperty("备注")
    private String remark;
}
