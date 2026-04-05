package com.aicoupledish.domain.req;

import lombok.Data;

import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

/**
 * 打卡请求
 */
@Data
public class CheckinReq {

    /**
     * 挑战ID
     */
    @NotNull(message = "挑战ID不能为空")
    private Long challengeId;

    /**
     * 打卡内容
     */
    @Size(max = 512, message = "打卡内容最长512个字符")
    private String content;

    /**
     * 打卡图片
     */
    private String imageUrl;
}
