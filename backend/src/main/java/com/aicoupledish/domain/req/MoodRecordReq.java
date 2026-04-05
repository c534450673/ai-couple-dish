package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 心情记录请求
 */
@Data
@ApiModel("心情记录请求")
public class MoodRecordReq {

    @NotBlank(message = "心情类型不能为空")
    @ApiModelProperty(value = "心情类型: happy/tired/upset/miss_you/love/sad/angry/anxious", required = true)
    private String moodType;

    @ApiModelProperty("心情描述")
    private String description;
}
