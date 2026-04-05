package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotNull;

/**
 * 发送每日问候请求
 */
@Data
@ApiModel("发送每日问候请求")
public class DailyGreetingReq {

    @NotNull(message = "问候类型不能为空")
    @ApiModelProperty(value = "类型: 1-早安 2-晚安", required = true)
    private Integer greetingType;

    @ApiModelProperty("文字内容")
    private String content;

    @ApiModelProperty("语音文件URL")
    private String voiceUrl;

    @ApiModelProperty("语音时长(秒)")
    private Integer voiceDuration;
}
