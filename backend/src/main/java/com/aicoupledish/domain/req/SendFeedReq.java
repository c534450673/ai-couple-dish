package com.aicoupledish.domain.req;

import lombok.Data;
import javax.validation.constraints.NotBlank;
import java.util.List;

/**
 * 发送投喂请求
 */
@Data
public class SendFeedReq {

    /**
     * 投喂类型：meal-正餐 dessert-甜品 snack-小吃 drink-饮品
     */
    @NotBlank(message = "投喂类型不能为空")
    private String feedType;

    /**
     * 投喂内容描述
     */
    private String content;

    /**
     * 图片URLs
     */
    private List<String> imageUrls;

    /**
     * 留言
     */
    private String message;
}