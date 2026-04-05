package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotNull;

/**
 * 提醒配置请求
 */
@Data
@ApiModel("提醒配置请求")
public class ReminderConfigReq {

    @NotNull(message = "纪念日ID不能为空")
    @ApiModelProperty(value = "纪念日ID", required = true)
    private Long anniversaryId;

    @ApiModelProperty("是否开启自动提醒：0-否 1-是")
    private Integer autoRemind;

    @ApiModelProperty("提前提醒天数")
    private Integer remindDaysBefore;

    @ApiModelProperty("提醒渠道：逗号分隔，如 app,wechat,sms")
    private String remindChannels;

    @ApiModelProperty("提醒时间（小时），如 9 表示早上9点")
    private Integer remindHour;

    @ApiModelProperty("是否启用微信提醒：0-否 1-是")
    private Integer wechatRemindEnabled;

    @ApiModelProperty("是否启用短信提醒：0-否 1-是")
    private Integer smsRemindEnabled;

    @ApiModelProperty("是否启用APP推送：0-否 1-是")
    private Integer appRemindEnabled;
}
