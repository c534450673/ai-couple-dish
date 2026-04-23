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
import java.util.List;

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
        Long userId = getCurrentUserId(request, jwtUtils);
        Long menuId = menuService.addMenu(userId, req);
        return Result.success("菜单添加成功", menuId);
    }

    @ApiOperation("更新菜单")
    @PutMapping("/update/{id}")
    public Result<Void> updateMenu(@PathVariable Long id, @RequestBody AddMenuReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        menuService.updateMenu(userId, id, req);
        return Result.success();
    }

    @ApiOperation("删除菜单")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        menuService.deleteMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("恢复菜单")
    @PostMapping("/recover/{id}")
    public Result<Void> recoverMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        menuService.recoverMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("点赞菜单")
    @PostMapping("/like/{id}")
    public Result<Void> likeMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        menuService.likeMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("取消点赞")
    @DeleteMapping("/unlike/{id}")
    public Result<Void> unlikeMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        menuService.unlikeMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("收藏菜单")
    @PostMapping("/favorite/{id}")
    public Result<Void> favoriteMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        menuService.favoriteMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("取消收藏")
    @DeleteMapping("/unfavorite/{id}")
    public Result<Void> unfavoriteMenu(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        menuService.unfavoriteMenu(userId, id);
        return Result.success();
    }

    @ApiOperation("获取菜单统计")
    @GetMapping("/stats")
    public Result<Object> getMenuStats() {
        Long userId = getCurrentUserId(request, jwtUtils);
        Object stats = menuService.getMenuStats(userId);
        return Result.success(stats);
    }

    @ApiOperation("获取附近的餐厅")
    @GetMapping("/nearby")
    public Result<List<MenuDTO>> getNearbyRestaurants(
            @RequestParam BigDecimal latitude,
            @RequestParam BigDecimal longitude,
            @RequestParam(required = false, defaultValue = "5000") Integer radiusMeters,
            @RequestParam(required = false) Integer status) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<MenuDTO> result = menuService.getNearbyRestaurants(userId, latitude, longitude, radiusMeters, status);
        return Result.success(result);
    }

    @ApiOperation("根据位置获取餐厅地图数据")
    @GetMapping("/map")
    public Result<List<MenuDTO>> getMapRestaurants(
            @RequestParam(required = false) BigDecimal centerLat,
            @RequestParam(required = false) BigDecimal centerLng,
            @RequestParam(required = false, defaultValue = "10") Integer zoomLevel) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<MenuDTO> result = menuService.getMapRestaurants(userId, centerLat, centerLng, zoomLevel);
        return Result.success(result);
    }

}