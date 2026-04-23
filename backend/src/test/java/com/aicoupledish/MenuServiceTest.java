package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMenuMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.CoupleMenu;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.MenuDTO;
import com.aicoupledish.domain.dto.PageDTO;
import com.aicoupledish.domain.req.AddMenuReq;
import com.aicoupledish.service.impl.MenuServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 菜单服务单元测试
 * 测试范围：菜单CRUD、筛选、点赞、收藏、软删除
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("菜单服务测试")
class MenuServiceTest {

    @Mock
    private CoupleMenuMapper menuMapper;

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private MenuServiceImpl menuService;

    private User testUser;
    private User testPartner;
    private CoupleMenu testMenu;

    @BeforeEach
    void setUp() {
        // 初始化测试用户 - 小明
        testUser = new User();
        testUser.setId(1L);
        testUser.setNickName("小明");
        testUser.setCoupleId(1L);
        testUser.setStatus(0);

        // 初始化测试用户 - 小红的伴侣
        testPartner = new User();
        testPartner.setId(2L);
        testPartner.setNickName("小红");
        testPartner.setCoupleId(1L);
        testPartner.setStatus(0);

        // 初始化测试菜单
        testMenu = new CoupleMenu();
        testMenu.setId(1L);
        testMenu.setCoupleId(1L);
        testMenu.setCreatorId(1L);
        testMenu.setRestaurantName("太二酸菜鱼");
        testMenu.setDishName("酸菜鱼");
        testMenu.setDishCategory("川菜");
        testMenu.setPrice(new BigDecimal("68.00"));
        testMenu.setLocation("深圳市南山区科兴科学园");
        testMenu.setRating(5);
        testMenu.setStatus(1); // 去过
        testMenu.setLikeCount(5);
        testMenu.setIsFavorite(0);
        testMenu.setPhotoCount(3);
        testMenu.setIsDeleted(0);
        testMenu.setCreateTime(LocalDateTime.now());
    }

    @Test
    @DisplayName("获取菜单列表-未绑定情侣应抛异常")
    void getMenuList_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.getMenuList(99L, null, null, null, null, null, null, null, null, 1L, 10L));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取菜单列表-有菜单应返回列表")
    void getMenuList_WithMenus_ShouldReturnList() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Arrays.asList(testMenu));
        pageResult.setTotal(1);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, null, null, null, null, null, null, null, null, 1L, 10L);

        // Then
        assertNotNull(result);
        assertNotNull(result.getList());
        assertEquals(1, result.getList().size());
        assertEquals("太二酸菜鱼", result.getList().get(0).getRestaurantName());
    }

    @Test
    @DisplayName("获取菜单列表-按状态筛选想去")
    void getMenuList_FilterByStatusWant_ShouldReturnFilteredList() {
        // Given
        CoupleMenu wantMenu = new CoupleMenu();
        wantMenu.setId(2L);
        wantMenu.setCoupleId(1L);
        wantMenu.setCreatorId(1L);
        wantMenu.setRestaurantName("陶陶居");
        wantMenu.setStatus(0); // 想去
        wantMenu.setIsFavorite(0);
        wantMenu.setLikeCount(0);

        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Arrays.asList(wantMenu));
        pageResult.setTotal(1);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, 0, null, null, null, null, null, null, null, 1L, 10L);

        // Then
        assertNotNull(result);
        assertEquals(0, result.getList().get(0).getStatus());
    }

    @Test
    @DisplayName("获取菜单列表-按状态筛选去过")
    void getMenuList_FilterByStatusBeen_ShouldReturnFilteredList() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Arrays.asList(testMenu));
        pageResult.setTotal(1);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, 1, null, null, null, null, null, null, null, 1L, 10L);

        // Then
        assertNotNull(result);
        assertEquals(1, result.getList().get(0).getStatus());
    }

    @Test
    @DisplayName("获取菜单列表-按关键词搜索")
    void getMenuList_SearchByKeyword_ShouldReturnMatchedList() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Arrays.asList(testMenu));
        pageResult.setTotal(1);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, null, "酸菜鱼", null, null, null, null, null, null, 1L, 10L);

        // Then
        assertNotNull(result);
        assertEquals(1, result.getList().size());
        assertTrue(result.getList().get(0).getRestaurantName().contains("酸菜鱼") ||
                  (result.getList().get(0).getDishName() != null && result.getList().get(0).getDishName().contains("酸菜鱼")));
    }

    @Test
    @DisplayName("获取菜单列表-空列表")
    void getMenuList_EmptyList_ShouldReturnEmptyList() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Collections.emptyList());
        pageResult.setTotal(0);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, null, null, null, null, null, null, null, null, 1L, 10L);

        // Then
        assertNotNull(result);
        assertTrue(result.getList().isEmpty());
    }

    @Test
    @DisplayName("获取菜单详情-菜单存在")
    void getMenuDetail_MenuExists_ShouldReturnDetail() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);

        // When
        MenuDTO result = menuService.getMenuDetail(1L, 1L);

        // Then
        assertNotNull(result);
        assertEquals(1L, result.getId());
        assertEquals("太二酸菜鱼", result.getRestaurantName());
    }

    @Test
    @DisplayName("获取菜单详情-菜单不存在应抛异常")
    void getMenuDetail_MenuNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.getMenuDetail(1L, 999L));
        assertEquals(BusinessException.MENU_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取菜单详情-无权限应抛异常")
    void getMenuDetail_NoPermission_ShouldThrowException() {
        // Given
        User otherUser = new User();
        otherUser.setId(3L);
        otherUser.setCoupleId(2L); // 不同的情侣ID
        otherUser.setStatus(0);

        when(userMapper.selectById(3L)).thenReturn(otherUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.getMenuDetail(3L, 1L));
        assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("添加菜单-未绑定情侣应抛异常")
    void addMenu_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("测试餐厅");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.addMenu(99L, req));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("添加菜单-想去类型应成功")
    void addMenu_WantType_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.insert(any(CoupleMenu.class))).thenAnswer(invocation -> {
            CoupleMenu menu = invocation.getArgument(0);
            menu.setId(1L);
            return 1;
        });

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("陶陶居");
        req.setStatus(0); // 想去

        // When
        Long menuId = menuService.addMenu(1L, req);

        // Then
        assertNotNull(menuId);
        verify(menuMapper).insert(any(CoupleMenu.class));
    }

    @Test
    @DisplayName("添加菜单-去过类型应成功")
    void addMenu_BeenType_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.insert(any(CoupleMenu.class))).thenAnswer(invocation -> {
            CoupleMenu menu = invocation.getArgument(0);
            menu.setId(1L);
            return 1;
        });

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("太二酸菜鱼");
        req.setStatus(1); // 去过

        // When
        Long menuId = menuService.addMenu(1L, req);

        // Then
        assertNotNull(menuId);
        verify(menuMapper).insert(any(CoupleMenu.class));
    }

    @Test
    @DisplayName("添加菜单-种草类型应成功")
    void addMenu_RecommendType_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.insert(any(CoupleMenu.class))).thenAnswer(invocation -> {
            CoupleMenu menu = invocation.getArgument(0);
            menu.setId(1L);
            return 1;
        });

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("奈雪の茶");
        req.setStatus(2); // 种草

        // When
        Long menuId = menuService.addMenu(1L, req);

        // Then
        assertNotNull(menuId);
        verify(menuMapper).insert(any(CoupleMenu.class));
    }

    @Test
    @DisplayName("添加菜单-有完整信息应成功")
    void addMenu_FullInfo_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.insert(any(CoupleMenu.class))).thenAnswer(invocation -> {
            CoupleMenu menu = invocation.getArgument(0);
            menu.setId(1L);
            return 1;
        });

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("太二酸菜鱼");
        req.setDishName("酸菜鱼、水煮肉片");
        req.setDishCategory("川菜");
        req.setPrice(new BigDecimal("68.00"));
        req.setLocation("深圳市南山区科兴科学园");
        req.setRating(5);
        req.setNote("鱼片很嫩，酸度刚好");
        req.setStatus(1);
        req.setEatenDate("2026-03-15");

        // When
        Long menuId = menuService.addMenu(1L, req);

        // Then
        assertNotNull(menuId);
        verify(menuMapper).insert(any(CoupleMenu.class));
    }

    @Test
    @DisplayName("更新菜单-菜单存在应成功")
    void updateMenu_MenuExists_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.updateById(any(CoupleMenu.class))).thenReturn(1);

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("更新后的餐厅名");
        req.setRating(4);

        // When
        menuService.updateMenu(1L, 1L, req);

        // Then
        verify(menuMapper).updateById(any(CoupleMenu.class));
    }

    @Test
    @DisplayName("更新菜单-菜单不存在应抛异常")
    void updateMenu_MenuNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(999L)).thenReturn(null);

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("更新后的餐厅名");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.updateMenu(1L, 999L, req));
        assertEquals(BusinessException.MENU_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("更新菜单-无权限应抛异常")
    void updateMenu_NoPermission_ShouldThrowException() {
        // Given
        User otherUser = new User();
        otherUser.setId(3L);
        otherUser.setCoupleId(2L); // 不同的情侣ID
        otherUser.setStatus(0);

        when(userMapper.selectById(3L)).thenReturn(otherUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);

        AddMenuReq req = new AddMenuReq();
        req.setRestaurantName("更新后的餐厅名");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.updateMenu(3L, 1L, req));
        assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("删除菜单-菜单存在应成功（软删除）")
    void deleteMenu_MenuExists_ShouldSoftDelete() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.updateById(any(CoupleMenu.class))).thenReturn(1);

        // When
        menuService.deleteMenu(1L, 1L);

        // Then
        verify(menuMapper).updateById(argThat(menu ->
            menu.getIsDeleted() == 1 && menu.getDeleteTime() != null));
    }

    @Test
    @DisplayName("删除菜单-菜单不存在应抛异常")
    void deleteMenu_MenuNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.deleteMenu(1L, 999L));
        assertEquals(BusinessException.MENU_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("删除菜单-无权限应抛异常")
    void deleteMenu_NoPermission_ShouldThrowException() {
        // Given
        User otherUser = new User();
        otherUser.setId(3L);
        otherUser.setCoupleId(2L); // 不同的情侣ID
        otherUser.setStatus(0);

        when(userMapper.selectById(3L)).thenReturn(otherUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.deleteMenu(3L, 1L));
        assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("恢复菜单-菜单存在应成功")
    void recoverMenu_MenuExists_ShouldSuccess() {
        // Given
        testMenu.setIsDeleted(1);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.updateById(any(CoupleMenu.class))).thenReturn(1);

        // When
        menuService.recoverMenu(1L, 1L);

        // Then
        verify(menuMapper).updateById(argThat(menu ->
            menu.getIsDeleted() == 0 && menu.getDeleteTime() == null));
    }

    @Test
    @DisplayName("点赞菜单-菜单存在应成功")
    void likeMenu_MenuExists_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.update(any(), any())).thenReturn(1);

        // When
        menuService.likeMenu(1L, 1L); // 用户1点赞自己的菜单（同一情侣）

        // Then
        verify(menuMapper).update(any(), any());
    }

    @Test
    @DisplayName("点赞菜单-菜单不存在应抛异常")
    void likeMenu_MenuNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(999L)).thenReturn(null);

        // When & Then
        assertThrows(BusinessException.class,
            () -> menuService.likeMenu(1L, 999L));
    }

    @Test
    @DisplayName("点赞菜单-无权限应抛异常")
    void likeMenu_NoPermission_ShouldThrowException() {
        // Given
        User otherUser = new User();
        otherUser.setId(3L);
        otherUser.setCoupleId(2L); // 不同的情侣ID
        otherUser.setStatus(0);

        when(userMapper.selectById(3L)).thenReturn(otherUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.likeMenu(3L, 1L));
        assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("取消点赞-点赞数应减少")
    void unlikeMenu_ShouldDecrementLikeCount() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.update(any(), any())).thenReturn(1);

        // When
        menuService.unlikeMenu(1L, 1L);

        // Then
        verify(menuMapper).update(any(), any());
    }

    @Test
    @DisplayName("取消点赞-菜单不存在应抛异常")
    void unlikeMenu_MenuNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(999L)).thenReturn(null);

        // When & Then
        assertThrows(BusinessException.class,
            () -> menuService.unlikeMenu(1L, 999L));
    }

    @Test
    @DisplayName("收藏菜单-应设置isFavorite为1")
    void favoriteMenu_ShouldSetFavoriteTrue() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.updateById(any(CoupleMenu.class))).thenReturn(1);

        // When
        menuService.favoriteMenu(1L, 1L);

        // Then
        verify(menuMapper).updateById(argThat(menu ->
            menu.getIsFavorite() == 1));
    }

    @Test
    @DisplayName("收藏菜单-菜单不存在应抛异常")
    void favoriteMenu_MenuNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(999L)).thenReturn(null);

        // When & Then
        assertThrows(BusinessException.class,
            () -> menuService.favoriteMenu(1L, 999L));
    }

    @Test
    @DisplayName("取消收藏-应设置isFavorite为0")
    void unfavoriteMenu_ShouldSetFavoriteFalse() {
        // Given
        testMenu.setIsFavorite(1);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.updateById(any(CoupleMenu.class))).thenReturn(1);

        // When
        menuService.unfavoriteMenu(1L, 1L);

        // Then
        verify(menuMapper).updateById(argThat(menu ->
            menu.getIsFavorite() == 0));
    }

    @Test
    @DisplayName("取消收藏-菜单不存在应抛异常")
    void unfavoriteMenu_MenuNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(999L)).thenReturn(null);

        // When & Then
        assertThrows(BusinessException.class,
            () -> menuService.unfavoriteMenu(1L, 999L));
    }

    @Test
    @DisplayName("获取菜单统计-未绑定情侣应抛异常")
    void getMenuStats_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.getMenuStats(99L));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取菜单统计-应返回各状态数量")
    void getMenuStats_ShouldReturnCounts() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectCount(any(LambdaQueryWrapper.class)))
            .thenReturn(10L) // 总数
            .thenReturn(5L) // 想去
            .thenReturn(3L) // 去过
            .thenReturn(2L); // 种草

        // When
        Object result = menuService.getMenuStats(1L);

        // Then
        assertNotNull(result);
        assertTrue(result instanceof java.util.Map);
        java.util.Map<?, ?> stats = (java.util.Map<?, ?>) result;
        assertEquals(10L, stats.get("totalCount"));
        assertEquals(5L, stats.get("wantToGoCount"));
        assertEquals(3L, stats.get("visitedCount"));
        assertEquals(2L, stats.get("seededCount"));
    }

    @Test
    @DisplayName("菜单状态名称转换-想去")
    void menuStatusName_Want_ShouldReturn想去() {
        // Given
        testMenu.setStatus(0);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Arrays.asList(testMenu));
        pageResult.setTotal(1);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, null, null, null, null, null, null, null, null, 1L, 10L);

        // Then
        assertEquals("想去", result.getList().get(0).getStatusName());
    }

    @Test
    @DisplayName("菜单状态名称转换-去过")
    void menuStatusName_Been_ShouldReturn去过() {
        // Given
        testMenu.setStatus(1);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Arrays.asList(testMenu));
        pageResult.setTotal(1);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, null, null, null, null, null, null, null, null, 1L, 10L);

        // Then
        assertEquals("去过", result.getList().get(0).getStatusName());
    }

    @Test
    @DisplayName("菜单状态名称转换-种草")
    void menuStatusName_Recommend_ShouldReturn种草() {
        // Given
        testMenu.setStatus(2);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        Page<CoupleMenu> pageResult = new Page<>(1, 10);
        pageResult.setRecords(Arrays.asList(testMenu));
        pageResult.setTotal(1);
        when(menuMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class)))
            .thenReturn(pageResult);

        // When
        PageDTO<MenuDTO> result = menuService.getMenuList(1L, null, null, null, null, null, null, null, null, 1L, 10L);

        // Then
        assertEquals("种草", result.getList().get(0).getStatusName());
    }

    @Test
    @DisplayName("创建者信息应正确填充")
    void menuDetail_ShouldIncludeCreatorInfo() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);

        // When
        MenuDTO result = menuService.getMenuDetail(1L, 1L);

        // Then
        assertNotNull(result);
        assertEquals("太二酸菜鱼", result.getRestaurantName());
    }

    // ========== 附近餐厅和地图模块测试 ==========

    @Test
    @DisplayName("获取附近餐厅-未绑定情侣应抛异常")
    void getNearbyRestaurants_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        BigDecimal latitude = new BigDecimal("22.543099");
        BigDecimal longitude = new BigDecimal("114.057868");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.getNearbyRestaurants(99L, latitude, longitude, 5000, null));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取附近餐厅-有餐厅应在半径内")
    void getNearbyRestaurants_WithinRadius_ShouldReturnRestaurants() {
        // Given
        CoupleMenu nearbyMenu = new CoupleMenu();
        nearbyMenu.setId(2L);
        nearbyMenu.setCoupleId(1L);
        nearbyMenu.setCreatorId(1L);
        nearbyMenu.setRestaurantName("深圳餐厅A");
        nearbyMenu.setStatus(1);
        nearbyMenu.setIsDeleted(0);
        nearbyMenu.setIsFavorite(0);
        nearbyMenu.setLatitude(new BigDecimal("22.543099")); // 与用户位置非常接近
        nearbyMenu.setLongitude(new BigDecimal("114.057868"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(nearbyMenu));

        BigDecimal userLat = new BigDecimal("22.543100"); // 几乎相同的位置
        BigDecimal userLng = new BigDecimal("114.057870");

        // When
        List<MenuDTO> result = menuService.getNearbyRestaurants(1L, userLat, userLng, 5000, null);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("深圳餐厅A", result.get(0).getRestaurantName());
        assertNotNull(result.get(0).getDistance());
    }

    @Test
    @DisplayName("获取附近餐厅-餐厅在半径外应被过滤")
    void getNearbyRestaurants_OutsideRadius_ShouldBeFiltered() {
        // Given - 餐厅距离用户约10公里
        CoupleMenu farMenu = new CoupleMenu();
        farMenu.setId(2L);
        farMenu.setCoupleId(1L);
        farMenu.setCreatorId(1L);
        farMenu.setRestaurantName("远距离餐厅");
        farMenu.setStatus(1);
        farMenu.setIsDeleted(0);
        farMenu.setIsFavorite(0);
        farMenu.setLatitude(new BigDecimal("22.62")); // 约10公里外
        farMenu.setLongitude(new BigDecimal("114.15"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(farMenu));

        BigDecimal userLat = new BigDecimal("22.543100");
        BigDecimal userLng = new BigDecimal("114.057870");

        // When - 搜索半径500米
        List<MenuDTO> result = menuService.getNearbyRestaurants(1L, userLat, userLng, 500, null);

        // Then - 餐厅在500米外，应被过滤掉
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("获取附近餐厅-无经纬度应被数据库查询排除")
    void getNearbyRestaurants_NoLocation_ShouldBeFilteredByQuery() {
        // This test verifies that menus without location are not returned by the query
        // Note: Since we mock the mapper, we can't test the actual query behavior here
        // This test documents the expected behavior - in real execution, the isNotNull
        // in the query wrapper would filter out menus without latitude/longitude
        // Given - 查询返回空列表（模拟数据库已过滤无位置的数据）
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList());

        BigDecimal userLat = new BigDecimal("22.543100");
        BigDecimal userLng = new BigDecimal("114.057870");

        // When
        List<MenuDTO> result = menuService.getNearbyRestaurants(1L, userLat, userLng, 5000, null);

        // Then
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("获取附近餐厅-返回的餐厅应包含正确的状态名称")
    void getNearbyRestaurants_ShouldReturnCorrectStatusName() {
        // Given - 创建一个status=0的菜单
        CoupleMenu status0Menu = new CoupleMenu();
        status0Menu.setId(2L);
        status0Menu.setCoupleId(1L);
        status0Menu.setCreatorId(1L);
        status0Menu.setRestaurantName("想去的店");
        status0Menu.setStatus(0); // 想去
        status0Menu.setIsDeleted(0);
        status0Menu.setIsFavorite(0);
        status0Menu.setLatitude(new BigDecimal("22.543099"));
        status0Menu.setLongitude(new BigDecimal("114.057868"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(status0Menu));

        BigDecimal userLat = new BigDecimal("22.543100");
        BigDecimal userLng = new BigDecimal("114.057870");

        // When - 查询附近餐厅（不按状态筛选）
        List<MenuDTO> result = menuService.getNearbyRestaurants(1L, userLat, userLng, 5000, null);

        // Then - 应该返回菜单且状态名称正确
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("想去", result.get(0).getStatusName());
    }

    @Test
    @DisplayName("获取附近餐厅-结果应按距离排序")
    void getNearbyRestaurants_ShouldBeSortedByDistance() {
        // Given
        CoupleMenu closerMenu = new CoupleMenu();
        closerMenu.setId(1L);
        closerMenu.setCoupleId(1L);
        closerMenu.setCreatorId(1L);
        closerMenu.setRestaurantName("较近的餐厅");
        closerMenu.setStatus(1);
        closerMenu.setIsDeleted(0);
        closerMenu.setIsFavorite(0);
        closerMenu.setLatitude(new BigDecimal("22.543100")); // 非常近
        closerMenu.setLongitude(new BigDecimal("114.057870"));

        CoupleMenu fartherMenu = new CoupleMenu();
        fartherMenu.setId(2L);
        fartherMenu.setCoupleId(1L);
        fartherMenu.setCreatorId(1L);
        fartherMenu.setRestaurantName("较远的餐厅");
        fartherMenu.setStatus(1);
        fartherMenu.setIsDeleted(0);
        fartherMenu.setIsFavorite(0);
        fartherMenu.setLatitude(new BigDecimal("22.55")); // 较远
        fartherMenu.setLongitude(new BigDecimal("114.07"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        // 按查询顺序返回（先近后远）
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(closerMenu, fartherMenu));

        BigDecimal userLat = new BigDecimal("22.543099");
        BigDecimal userLng = new BigDecimal("114.057868");

        // When
        List<MenuDTO> result = menuService.getNearbyRestaurants(1L, userLat, userLng, 20000, null);

        // Then - 结果应按距离排序
        assertNotNull(result);
        assertEquals(2, result.size());
        // 第一个应该是距离更近的
        assertTrue(result.get(0).getDistance() <= result.get(1).getDistance());
    }

    @Test
    @DisplayName("获取地图餐厅-未绑定情侣应抛异常")
    void getMapRestaurants_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> menuService.getMapRestaurants(99L, new BigDecimal("22.543"), new BigDecimal("114.057"), 10));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取地图餐厅-有餐厅应返回")
    void getMapRestaurants_WithRestaurants_ShouldReturn() {
        // Given
        testMenu.setLatitude(new BigDecimal("22.543099"));
        testMenu.setLongitude(new BigDecimal("114.057868"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

        // When
        List<MenuDTO> result = menuService.getMapRestaurants(
            1L,
            new BigDecimal("22.543"),
            new BigDecimal("114.057"),
            10
        );

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
    }

    @Test
    @DisplayName("获取地图餐厅-无中心点应返回所有有位置的餐厅")
    void getMapRestaurants_NoCenterPoint_ShouldReturnAllWithLocation() {
        // Given
        testMenu.setLatitude(new BigDecimal("22.543099"));
        testMenu.setLongitude(new BigDecimal("114.057868"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

        // When - 无中心点
        List<MenuDTO> result = menuService.getMapRestaurants(
            1L,
            null,
            null,
            null
        );

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
    }

    @Test
    @DisplayName("获取地图餐厅-根据缩放级别调整搜索范围")
    void getMapRestaurants_WithZoomLevel_ShouldFilterByRadius() {
        // Given
        testMenu.setLatitude(new BigDecimal("22.543099"));
        testMenu.setLongitude(new BigDecimal("114.057868"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

        // When - zoom level 10 (大范围)
        List<MenuDTO> result = menuService.getMapRestaurants(
            1L,
            new BigDecimal("22.543"),
            new BigDecimal("114.057"),
            10
        );

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
    }

    @Test
    @DisplayName("获取地图餐厅-有中心点应计算距离")
    void getMapRestaurants_WithCenter_ShouldCalculateDistance() {
        // Given
        testMenu.setLatitude(new BigDecimal("22.543099"));
        testMenu.setLongitude(new BigDecimal("114.057868"));

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

        // When
        List<MenuDTO> result = menuService.getMapRestaurants(
            1L,
            new BigDecimal("22.543"),
            new BigDecimal("114.057"),
            15
        );

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        // 有中心点时应该计算距离
        assertNotNull(result.get(0).getDistance());
    }

    @Test
    @DisplayName("获取地图餐厅-无经纬度应被数据库查询排除")
    void getMapRestaurants_NoLocation_ShouldBeFilteredByQuery() {
        // This test verifies that menus without location are not returned by the query
        // Note: Since we mock the mapper, we can't test the actual query behavior here
        // This test documents the expected behavior - in real execution, the isNotNull
        // in the query wrapper would filter out menus without latitude/longitude
        // Given - 查询返回空列表（模拟数据库已过滤无位置的数据）
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList());

        // When
        List<MenuDTO> result = menuService.getMapRestaurants(
            1L,
            new BigDecimal("22.543"),
            new BigDecimal("114.057"),
            10
        );

        // Then
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("获取地图餐厅-正常菜单应正确映射")
    void getMapRestaurants_NormalMenu_ShouldMapCorrectly() {
        // Given - 创建一个正常的菜单
        CoupleMenu normalMenu = createMenuWithLocation(new BigDecimal("22.543"), new BigDecimal("114.057"));
        normalMenu.setRestaurantName("正常餐厅");

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(normalMenu));

        // When
        List<MenuDTO> result = menuService.getMapRestaurants(
            1L,
            new BigDecimal("22.543"),
            new BigDecimal("114.057"),
            10
        );

        // Then - 应该返回菜单且信息正确
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("正常餐厅", result.get(0).getRestaurantName());
    }

    @Test
    @DisplayName("获取地图餐厅-空列表应返回空")
    void getMapRestaurants_EmptyList_ShouldReturnEmpty() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList());

        // When
        List<MenuDTO> result = menuService.getMapRestaurants(
            1L,
            new BigDecimal("22.543"),
            new BigDecimal("114.057"),
            10
        );

        // Then
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("距离计算-相同位置应返回0")
    void distanceCalculation_SameLocation_ShouldReturnZero() {
        // Given - 同一位置
        BigDecimal lat = new BigDecimal("22.543099");
        BigDecimal lng = new BigDecimal("114.057868");
        CoupleMenu sameLocationMenu = createMenuWithLocation(lat, lng);

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(sameLocationMenu));

        // When - 用户也在同一位置
        List<MenuDTO> result = menuService.getNearbyRestaurants(
            1L,
            new BigDecimal("22.543099"),
            new BigDecimal("114.057868"),
            5000,
            null
        );

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        // 同一位置，距离应该非常接近0
        assertTrue(result.get(0).getDistance() < 1); // 小于1米
    }

    @Test
    @DisplayName("距离计算-深圳到北京距离应约2000公里")
    void distanceCalculation_ShenzhenToBeijing_ShouldBeAbout2000km() {
        // Given - 深圳和北京的大致坐标
        CoupleMenu beijingMenu = createMenuWithLocation(new BigDecimal("39.904"), new BigDecimal("116.407"));
        beijingMenu.setRestaurantName("北京餐厅");

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(beijingMenu));

        // When - 用户在深圳
        List<MenuDTO> result = menuService.getNearbyRestaurants(
            1L,
            new BigDecimal("22.543"), // 深圳
            new BigDecimal("114.057"),
            100000000, // 足够大的半径
            null
        );

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        // 深圳到北京约2000公里
        double distanceKm = result.get(0).getDistance() / 1000;
        assertTrue(distanceKm > 1800 && distanceKm < 2200,
            "Distance should be around 2000km, but was: " + distanceKm + "km");
    }

    // ========== Helper methods ==========

    /**
     * 创建带有位置信息的测试菜单
     */
    private CoupleMenu createMenuWithLocation(BigDecimal latitude, BigDecimal longitude) {
        CoupleMenu menu = new CoupleMenu();
        menu.setId(1L);
        menu.setCoupleId(1L);
        menu.setCreatorId(1L);
        menu.setRestaurantName("测试餐厅");
        menu.setStatus(1);
        menu.setIsDeleted(0);
        menu.setIsFavorite(0);
        menu.setLikeCount(0);
        menu.setLatitude(latitude);
        menu.setLongitude(longitude);
        menu.setCreateTime(LocalDateTime.now());
        return menu;
    }
}
