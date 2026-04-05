package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.WishDTO;
import com.aicoupledish.service.WishService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 心愿单控制器
 */
@Api(tags = "心愿单模块")
@RestController
@RequestMapping("/wish")
@RequiredArgsConstructor
public class WishController extends BaseAuthController {

    private final WishService wishService;
    private final JwtUtils jwtUtils;
    private final HttpServletRequest request;

    @ApiOperation("获取心愿单列表")
    @GetMapping("/list")
    public Result<List<WishDTO>> getWishList() {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<WishDTO> list = wishService.getWishList(userId);
        return Result.success(list);
    }

    @ApiOperation("获取心愿单详情")
    @GetMapping("/detail/{id}")
    public Result<WishDTO> getWishDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        WishDTO wish = wishService.getWishDetail(userId, id);
        return Result.success(wish);
    }

    @ApiOperation("添加心愿")
    @PostMapping("/add")
    public Result<Long> addWish(
            @RequestParam String wishType,
            @RequestParam String title,
            @RequestParam(required = false) String description,
            @RequestParam(required = false) String imageUrl,
            @RequestParam(required = false) Integer priority) {
        Long userId = getCurrentUserId();
        Long wishId = wishService.addWish(userId, wishType, title, description, imageUrl, priority);
        return Result.success(wishId);
    }

    @ApiOperation("更新心愿")
    @PutMapping("/update/{id}")
    public Result<Void> updateWish(
            @PathVariable Long id,
            @RequestParam(required = false) String title,
            @RequestParam(required = false) String description,
            @RequestParam(required = false) String imageUrl,
            @RequestParam(required = false) Integer priority) {
        Long userId = getCurrentUserId();
        wishService.updateWish(userId, id, title, description, imageUrl, priority);
        return Result.success();
    }

    @ApiOperation("删除心愿")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteWish(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        wishService.deleteWish(userId, id);
        return Result.success();
    }

    @ApiOperation("实现心愿")
    @PostMapping("/fulfill/{id}")
    public Result<Void> fulfillWish(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        wishService.fulfillWish(userId, id);
        return Result.success();
    }

}
