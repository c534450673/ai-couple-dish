package com.aicoupledish.domain.req;

import lombok.Data;

import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.math.BigDecimal;

/**
 * 创建订单请求
 */
@Data
public class CreateOrderReq {

    /**
     * 菜谱ID
     */
    @NotNull(message = "菜谱ID不能为空")
    private Long recipeId;

    /**
     * 数量
     */
    private Integer quantity;

    /**
     * 配送地址
     */
    @Size(max = 512, message = "配送地址最长512个字符")
    private String address;

    /**
     * 备注
     */
    @Size(max = 512, message = "备注最长512个字符")
    private String remark;
}
