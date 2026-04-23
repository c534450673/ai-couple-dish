package com.aicoupledish.service;

import com.aicoupledish.domain.dto.MenuDTO;
import com.aicoupledish.domain.dto.PageDTO;
import com.aicoupledish.domain.req.AddMenuReq;

import java.math.BigDecimal;
import java.util.List;

/**
 * 菜单服务接口
 */
public interface MenuService {

    /**
     * 获取菜单列表（分页，支持多条件筛选和排序）
     * @param userId 用户ID
     * @param status 状态筛选
     * @param keyword 关键词搜索
     * @param dishCategory 菜品分类
     * @param minPrice 最低价格
     * @param maxPrice 最高价格
     * @param minRating 最低评分
     * @param sortBy 排序字段（time/rating/likeCount）
     * @param sortOrder 排序方向（asc/desc）
     * @param page 页码
     * @param pageSize 每页数量
     */
    PageDTO<MenuDTO> getMenuList(Long userId, Integer status, String keyword, String dishCategory,
                                   BigDecimal minPrice, BigDecimal maxPrice, Integer minRating,
                                   String sortBy, String sortOrder, Long page, Long pageSize);

    /**
     * 获取菜单详情
     */
    MenuDTO getMenuDetail(Long userId, Long menuId);

    /**
     * 添加菜单
     */
    Long addMenu(Long userId, AddMenuReq req);

    /**
     * 更新菜单
     */
    void updateMenu(Long userId, Long menuId, AddMenuReq req);

    /**
     * 删除菜单（软删除）
     */
    void deleteMenu(Long userId, Long menuId);

    /**
     * 恢复菜单
     */
    void recoverMenu(Long userId, Long menuId);

    /**
     * 点赞菜单
     */
    void likeMenu(Long userId, Long menuId);

    /**
     * 取消点赞
     */
    void unlikeMenu(Long userId, Long menuId);

    /**
     * 收藏菜单
     */
    void favoriteMenu(Long userId, Long menuId);

    /**
     * 取消收藏
     */
    void unfavoriteMenu(Long userId, Long menuId);

    /**
     * 获取菜单统计
     */
    Object getMenuStats(Long userId);

    /**
     * 获取附近的餐厅
     * @param userId 用户ID
     * @param latitude 当前纬度
     * @param longitude 当前经度
     * @param radiusMeters 搜索半径（米）
     * @param status 状态筛选
     */
    List<MenuDTO> getNearbyRestaurants(Long userId, BigDecimal latitude, BigDecimal longitude, Integer radiusMeters, Integer status);

    /**
     * 获取地图视图的餐厅数据
     * @param userId 用户ID
     * @param centerLat 中心纬度
     * @param centerLng 中心经度
     * @param zoomLevel 缩放级别
     */
    List<MenuDTO> getMapRestaurants(Long userId, BigDecimal centerLat, BigDecimal centerLng, Integer zoomLevel);
}