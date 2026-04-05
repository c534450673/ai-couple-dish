package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.MenuDTO;
import com.aicoupledish.domain.dto.PageDTO;
import com.aicoupledish.domain.req.AddMenuReq;
import com.aicoupledish.service.MenuService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.math.BigDecimal;

/**
 * 菜单控制器
 */
@Api(tags = "菜单模块")
@RestController
@RequestMapping("/menu")
@RequiredArgsConstructor
public class MenuController extends BaseAuthController {

    private final MenuService menuService;
    private final JwtUtils jwtUtils;

    private final HttpServletRequest request;

    @ApiOperation("获取菜单列表")
    @GetMapping("/list")
    public Result<PageDTO<MenuDTO>> getMenuList(
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String dishCategory,
            @RequestParam(required = false) BigDecimal minPrice,
            @RequestParam(required = false) BigDecimal maxPrice,
            @RequestParam(required = false) Integer minRating,
            @RequestParam(required = false) String sortBy,
            @RequestParam(required = false) String sortOrder,
            @RequestParam(required = false) Long page,
            @RequestParam(required = false) Long pageSize) {
        Long userId = getCurrentUserId(request, jwtUtils);
        PageDTO<MenuDTO> result = menuService.getMenuList(userId, status, keyword, dishCategory, minPrice, maxPrice, minRating, sortBy, sortOrder, page, pageSize);
        return Result.success(result);
    }

    @ApiOperation("获取菜单详情")
    @GetMapping("/detail/{id}")
    public Result<MenuDTO> getMenuDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        MenuDTO menu = menuService.getMenuDetail(userId, id);
        return Result.success(menu);
    }

    @ApiOperation("添加菜单")
    @PostMapping("/add")
    public Result<Long> addMenu(@Valid @RequestBody AddMenuReq req) {
        Long userId = getCurrentUserId();
        Long menuId = menuService.addMenu(userId, req);
        return Result.success("菜单添加成功", menuId);
    }

    @ApiOperation("更新菜单")
    @PutMapping("/update/{id}")
    public Result<Void> updateMenu(@PathVariable Long id, @RequestBody AddMenuReq req) {
        Long userId = getCurrentUserId();
        menuService.updateMenu(userId, id, req);
        return Result.success();
    }

    @ApiOperation("删除菜单")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        menuService.deleteMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("恢复菜单")
    @PostMapping("/recover/{id}")
    public Result<Void> recoverMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        menuService.recoverMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("点赞菜单")
    @PostMapping("/like/{id}")
    public Result<Void> likeMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        menuService.likeMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("取消点赞")
    @DeleteMapping("/unlike/{id}")
    public Result<Void> unlikeMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        menuService.unlikeMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("收藏菜单")
    @PostMapping("/favorite/{id}")
    public Result<Void> favoriteMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        menuService.favoriteMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("取消收藏")
    @DeleteMapping("/unfavorite/{id}")
    public Result<Void> unfavoriteMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId();
        menuService.unfavoriteMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("获取菜单统计")
    @GetMapping("/stats")
    public Result<Object> getMenuStats() {
        Long userId = getCurrentUserId();
        Object stats = menuService.getMenuStats(userId);
        return Result.success(stats);
    }

}