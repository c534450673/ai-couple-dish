package com.aicoupledish.domain.req;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.time.LocalDate;
import java.util.List;

/**
 * 创建时光胶囊请求
 */
@Data
@ApiModel("创建时光胶囊请求")
public class TimeCapsuleReq {

    @NotBlank(message = "胶囊类型不能为空")
    @ApiModelProperty(value = "胶囊类型：text/voice/video/photo", required = true)
    private String capsuleType;

    @ApiModelProperty("胶囊标题")
    private String title;

    @ApiModelProperty("胶囊内容（文本类型必填）")
    private String content;

    @ApiModelProperty("媒体URLs")
    private List<String> mediaUrls;

    @NotNull(message = "解锁日期不能为空")
    @ApiModelProperty(value = "解锁日期", required = true)
    private LocalDate unlockDate;
}
