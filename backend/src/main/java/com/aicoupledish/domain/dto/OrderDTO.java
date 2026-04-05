package com.aicoupledish.domain.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 订单DTO
 */
@Data
public class OrderDTO {

    /**
     * 订单ID
     */
    private Long id;

    /**
     * 情侣ID
     */
    private Long coupleId;

    /**
     * 买家ID
     */
    private Long buyerId;

    /**
     * 买家名称
     */
    private String buyerName;

    /**
     * 买家头像
     */
    private String buyerAvatar;

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
     * 菜谱ID
     */
    private Long recipeId;

    /**
     * 菜谱名称
     */
    private String recipeName;

    /**
     * 菜谱封面
     */
    private String recipeCoverUrl;

    /**
     * 数量
     */
    private Integer quantity;

    /**
     * 总价
     */
    private BigDecimal totalAmount;

    /**
     * 配送地址
     */
    private String address;

    /**
     * 状态
     */
    private Integer status;

    /**
     * 状态描述
     */
    private String statusDesc;

    /**
     * 备注
     */
    private String remark;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 支付时间
     */
    private LocalDateTime payTime;

    /**
     * 接单时间
     */
    private LocalDateTime acceptTime;

    /**
     * 完成时间
     */
    private LocalDateTime completeTime;

    /**
     * 取消时间
     */
    private LocalDateTime cancelTime;
}
