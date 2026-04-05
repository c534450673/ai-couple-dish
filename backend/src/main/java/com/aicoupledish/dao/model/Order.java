package com.aicoupledish.dao.model;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 订单表
 */
@Data
@TableName("t_order")
public class Order implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(type = IdType.AUTO)
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
     * 卖家ID
     */
    private Long sellerId;

    /**
     * 菜谱ID
     */
    private Long recipeId;

    /**
     * 菜谱名称
     */
    private String recipeName;

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
     * 状态：0-待接单 1-制作中 2-待送达 3-已完成 4-已取消 5-退款中 6-已退款
     */
    private Integer status;

    /**
     * 备注
     */
    private String remark;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
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
     * 开始制作时间
     */
    private LocalDateTime cookingStartTime;

    /**
     * 完成时间
     */
    private LocalDateTime completeTime;

    /**
     * 取消时间
     */
    private LocalDateTime cancelTime;
}
