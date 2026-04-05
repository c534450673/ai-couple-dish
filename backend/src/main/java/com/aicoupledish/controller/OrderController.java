package com.aicoupledish.controller;

import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.OrderDTO;
import com.aicoupledish.domain.req.CreateOrderReq;
import com.aicoupledish.service.OrderService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 订单控制器
 */
@Api(tags = "订单管理")
@RestController
@RequestMapping("/order")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    @ApiOperation("创建订单")
    @PostMapping("/create")
    public Result<Long> createOrder(
            @RequestAttribute("userId") Long userId,
            @Validated @RequestBody CreateOrderReq req) {
        Long orderId = orderService.createOrder(userId, req);
        return Result.success(orderId);
    }

    @ApiOperation("取消订单")
    @PostMapping("/cancel/{orderId}")
    public Result<Void> cancelOrder(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId) {
        orderService.cancelOrder(userId, orderId);
        return Result.success("取消成功");
    }

    @ApiOperation("接单")
    @PostMapping("/accept/{orderId}")
    public Result<Void> acceptOrder(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId) {
        orderService.acceptOrder(userId, orderId);
        return Result.success("接单成功");
    }

    @ApiOperation("开始制作")
    @PostMapping("/start-cooking/{orderId}")
    public Result<Void> startCooking(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId) {
        orderService.startCooking(userId, orderId);
        return Result.success("开始制作");
    }

    @ApiOperation("完成制作")
    @PostMapping("/finish-cooking/{orderId}")
    public Result<Void> finishCooking(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId) {
        orderService.finishCooking(userId, orderId);
        return Result.success("制作完成");
    }

    @ApiOperation("确认送达/完成订单")
    @PostMapping("/complete/{orderId}")
    public Result<Void> completeOrder(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId) {
        orderService.completeOrder(userId, orderId);
        return Result.success("订单完成");
    }

    @ApiOperation("申请退款")
    @PostMapping("/refund/{orderId}")
    public Result<Void> applyRefund(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId,
            @RequestParam(required = false) @ApiParam("退款原因") String reason) {
        orderService.applyRefund(userId, orderId, reason);
        return Result.success("退款申请已提交");
    }

    @ApiOperation("确认退款")
    @PostMapping("/confirm-refund/{orderId}")
    public Result<Void> confirmRefund(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId) {
        orderService.confirmRefund(userId, orderId);
        return Result.success("已确认退款");
    }

    @ApiOperation("获取订单详情")
    @GetMapping("/detail/{orderId}")
    public Result<OrderDTO> getOrderDetail(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long orderId) {
        OrderDTO dto = orderService.getOrderDetail(userId, orderId);
        return Result.success(dto);
    }

    @ApiOperation("获取我买的订单")
    @GetMapping("/my-buy")
    public Result<Page<OrderDTO>> getMyBuyOrders(
            @RequestAttribute("userId") Long userId,
            @RequestParam(required = false) @ApiParam("状态") Integer status,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<OrderDTO> page = orderService.getMyBuyOrders(userId, status, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("获取我卖的订单")
    @GetMapping("/my-sell")
    public Result<Page<OrderDTO>> getMySellOrders(
            @RequestAttribute("userId") Long userId,
            @RequestParam(required = false) @ApiParam("状态") Integer status,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<OrderDTO> page = orderService.getMySellOrders(userId, status, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("获取情侣的所有订单")
    @GetMapping("/couple")
    public Result<Page<OrderDTO>> getCoupleOrders(
            @RequestAttribute("userId") Long userId,
            @RequestParam(required = false) @ApiParam("状态") Integer status,
            @RequestParam(defaultValue = "1") @ApiParam("页码") Integer pageNum,
            @RequestParam(defaultValue = "10") @ApiParam("每页大小") Integer pageSize) {
        Page<OrderDTO> page = orderService.getCoupleOrders(userId, status, pageNum, pageSize);
        return Result.success(page);
    }

    @ApiOperation("获取待处理订单数量")
    @GetMapping("/pending-count")
    public Result<Integer> getPendingOrderCount(
            @RequestAttribute("userId") Long userId) {
        Integer count = orderService.getPendingOrderCount(userId);
        return Result.success(count);
    }
}
