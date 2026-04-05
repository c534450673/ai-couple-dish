package com.aicoupledish.domain.req;

import lombok.Data;

import javax.validation.constraints.NotNull;

/**
 * 添加购物车请求
 */
@Data
public class AddToCartReq {

    /**
     * 菜谱ID
     */
    @NotNull(message = "菜谱ID不能为空")
    private Long recipeId;

    /**
     * 数量
     */
    private Integer quantity;
}
