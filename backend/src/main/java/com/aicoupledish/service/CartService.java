package com.aicoupledish.service;

import com.aicoupledish.domain.dto.CartDTO;
import com.aicoupledish.domain.req.AddToCartReq;

import java.util.List;

/**
 * 购物车服务
 */
public interface CartService {

    /**
     * 添加到购物车
     *
     * @param userId 用户ID
     * @param req    添加请求
     * @return 购物车ID
     */
    Long addToCart(Long userId, AddToCartReq req);

    /**
     * 更新购物车数量
     *
     * @param userId 用户ID
     * @param cartId 购物车ID
     * @param quantity 数量
     */
    void updateQuantity(Long userId, Long cartId, Integer quantity);

    /**
     * 从购物车移除
     *
     * @param userId 用户ID
     * @param cartId 购物车ID
     */
    void removeFromCart(Long userId, Long cartId);

    /**
     * 批量移除
     *
     * @param userId  用户ID
     * @param cartIds 购物车ID列表
     */
    void batchRemove(Long userId, List<Long> cartIds);

    /**
     * 清空购物车
     *
     * @param userId 用户ID
     */
    void clearCart(Long userId);

    /**
     * 获取购物车列表
     *
     * @param userId 用户ID
     * @return 购物车列表
     */
    List<CartDTO> getCartList(Long userId);

    /**
     * 获取购物车数量
     *
     * @param userId 用户ID
     * @return 数量
     */
    Integer getCartCount(Long userId);

    /**
     * 选择购物车项目创建订单
     *
     * @param userId  用户ID
     * @param cartIds 购物车ID列表
     * @return 订单ID列表
     */
    List<Long> checkout(Long userId, List<Long> cartIds);
}
