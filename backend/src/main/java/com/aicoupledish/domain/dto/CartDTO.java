package com.aicoupledish.domain.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 购物车DTO
 */
@Data
public class CartDTO {

    /**
     * 购物车ID
     */
    private Long id;

    /**
     * 菜谱ID
     */
    private Long recipeId;

    /**
     * 菜谱标题
     */
    private String recipeTitle;

    /**
     * 菜谱封面
     */
    private String recipeCoverUrl;

    /**
     * 菜谱描述
     */
    private String recipeDescription;

    /**
     * 卖家ID
     */
    private Long sellerId;

    /**
     * 卖家名称
     */
    private String sellerName;

    /**
     * 卖家头像
     */
    private String sellerAvatar;

    /**
     * 数量
     */
    private Integer quantity;

    /**
     * 单价
     */
    private BigDecimal unitPrice;

    /**
     * 小计
     */
    private BigDecimal subtotal;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;
}
