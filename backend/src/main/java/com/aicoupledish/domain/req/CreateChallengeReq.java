package com.aicoupledish.domain.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.time.LocalDate;

/**
 * 创建挑战请求
 */
@Data
public class CreateChallengeReq {

    /**
     * 挑战类型
     */
    @NotBlank(message = "挑战类型不能为空")
    private String challengeType;

    /**
     * 挑战标题
     */
    @NotBlank(message = "挑战标题不能为空")
    @Size(max = 64, message = "挑战标题最长64个字符")
    private String title;

    /**
     * 挑战描述
     */
    @Size(max = 256, message = "挑战描述最长256个字符")
    private String description;

    /**
     * 目标天数
     */
    @NotNull(message = "目标天数不能为空")
    private Integer targetDays;

    /**
     * 开始日期（可选，默认今天）
     */
    private LocalDate startDate;

    /**
     * 奖励
     */
    @Size(max = 128, message = "奖励最长128个字符")
    private String reward;
}
