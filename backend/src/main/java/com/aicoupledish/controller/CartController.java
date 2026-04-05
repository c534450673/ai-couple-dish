package com.aicoupledish.controller;

import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.CartDTO;
import com.aicoupledish.domain.req.AddToCartReq;
import com.aicoupledish.service.CartService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 购物车控制器
 */
@Api(tags = "购物车管理")
@RestController
@RequestMapping("/cart")
@RequiredArgsConstructor
public class CartController {

    private final CartService cartService;

    @ApiOperation("添加到购物车")
    @PostMapping("/add")
    public Result<Long> addToCart(
            @RequestAttribute("userId") Long userId,
            @Validated @RequestBody AddToCartReq req) {
        Long cartId = cartService.addToCart(userId, req);
        return Result.success(cartId);
    }

    @ApiOperation("更新数量")
    @PutMapping("/quantity/{cartId}")
    public Result<Void> updateQuantity(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long cartId,
            @RequestParam @ApiParam("数量") Integer quantity) {
        cartService.updateQuantity(userId, cartId, quantity);
        return Result.success("更新成功");
    }

    @ApiOperation("移除购物车项目")
    @DeleteMapping("/remove/{cartId}")
    public Result<Void> removeFromCart(
            @RequestAttribute("userId") Long userId,
            @PathVariable Long cartId) {
        cartService.removeFromCart(userId, cartId);
        return Result.success("移除成功");
    }

    @ApiOperation("批量移除")
    @DeleteMapping("/batch-remove")
    public Result<Void> batchRemove(
            @RequestAttribute("userId") Long userId,
            @RequestBody @ApiParam("购物车ID列表") List<Long> cartIds) {
        cartService.batchRemove(userId, cartIds);
        return Result.success("移除成功");
    }

    @ApiOperation("清空购物车")
    @DeleteMapping("/clear")
    public Result<Void> clearCart(
            @RequestAttribute("userId") Long userId) {
        cartService.clearCart(userId);
        return Result.success("清空成功");
    }

    @ApiOperation("获取购物车列表")
    @GetMapping("/list")
    public Result<List<CartDTO>> getCartList(
            @RequestAttribute("userId") Long userId) {
        List<CartDTO> list = cartService.getCartList(userId);
        return Result.success(list);
    }

    @ApiOperation("获取购物车数量")
    @GetMapping("/count")
    public Result<Integer> getCartCount(
            @RequestAttribute("userId") Long userId) {
        Integer count = cartService.getCartCount(userId);
        return Result.success(count);
    }

    @ApiOperation("结算")
    @PostMapping("/checkout")
    public Result<List<Long>> checkout(
            @RequestAttribute("userId") Long userId,
            @RequestBody @ApiParam("购物车ID列表") List<Long> cartIds) {
        List<Long> orderIds = cartService.checkout(userId, cartIds);
        return Result.success(orderIds);
    }
}
