package com.aicoupledish.service;

import com.aicoupledish.domain.dto.OrderDTO;
import com.aicoupledish.domain.req.CreateOrderReq;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import java.util.List;

/**
 * 订单服务
 */
public interface OrderService {

    /**
     * 创建订单
     *
     * @param userId 用户ID
     * @param req    创建请求
     * @return 订单ID
     */
    Long createOrder(Long userId, CreateOrderReq req);

    /**
     * 取消订单
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     */
    void cancelOrder(Long userId, Long orderId);

    /**
     * 接单
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     */
    void acceptOrder(Long userId, Long orderId);

    /**
     * 开始制作
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     */
    void startCooking(Long userId, Long orderId);

    /**
     * 完成制作（待送达）
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     */
    void finishCooking(Long userId, Long orderId);

    /**
     * 确认送达/完成订单
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     */
    void completeOrder(Long userId, Long orderId);

    /**
     * 申请退款
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     * @param reason  退款原因
     */
    void applyRefund(Long userId, Long orderId, String reason);

    /**
     * 确认退款
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     */
    void confirmRefund(Long userId, Long orderId);

    /**
     * 获取订单详情
     *
     * @param userId  用户ID
     * @param orderId 订单ID
     * @return 订单详情
     */
    OrderDTO getOrderDetail(Long userId, Long orderId);

    /**
     * 获取我买的订单列表
     *
     * @param userId   用户ID
     * @param status   状态（可选）
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 订单分页
     */
    Page<OrderDTO> getMyBuyOrders(Long userId, Integer status, Integer pageNum, Integer pageSize);

    /**
     * 获取我卖的订单列表
     *
     * @param userId   用户ID
     * @param status   状态（可选）
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 订单分页
     */
    Page<OrderDTO> getMySellOrders(Long userId, Integer status, Integer pageNum, Integer pageSize);

    /**
     * 获取情侣的所有订单
     *
     * @param userId   用户ID
     * @param status   状态（可选）
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 订单分页
     */
    Page<OrderDTO> getCoupleOrders(Long userId, Integer status, Integer pageNum, Integer pageSize);

    /**
     * 获取待处理的订单数量
     *
     * @param userId 用户ID
     * @return 待处理数量（作为买家和卖家）
     */
    Integer getPendingOrderCount(Long userId);
}
