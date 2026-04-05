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
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

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

        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(wantMenu));

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
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

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
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

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
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Collections.emptyList());

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
        when(menuMapper.insert(any(CoupleMenu.class))).thenReturn(1);

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
        when(menuMapper.insert(any(CoupleMenu.class))).thenReturn(1);

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
        when(menuMapper.insert(any(CoupleMenu.class))).thenReturn(1);

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
        when(menuMapper.insert(any(CoupleMenu.class))).thenReturn(1);

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
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.update(any(), any())).thenReturn(1);

        // When
        menuService.likeMenu(2L, 1L); // 用户2点赞

        // Then
        verify(menuMapper).update(any(), any());
    }

    @Test
    @DisplayName("取消点赞-点赞数应减少")
    void unlikeMenu_ShouldDecrementLikeCount() {
        // Given
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.update(any(), any())).thenReturn(1);

        // When
        menuService.unlikeMenu(2L, 1L);

        // Then
        verify(menuMapper).update(any(), any());
    }

    @Test
    @DisplayName("收藏菜单-应设置isFavorite为1")
    void favoriteMenu_ShouldSetFavoriteTrue() {
        // Given
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.updateById(any(CoupleMenu.class))).thenReturn(1);

        // When
        menuService.favoriteMenu(1L, 1L);

        // Then
        verify(menuMapper).updateById(argThat(menu ->
            menu.getIsFavorite() == 1));
    }

    @Test
    @DisplayName("取消收藏-应设置isFavorite为0")
    void unfavoriteMenu_ShouldSetFavoriteFalse() {
        // Given
        testMenu.setIsFavorite(1);
        when(menuMapper.selectById(1L)).thenReturn(testMenu);
        when(menuMapper.updateById(any(CoupleMenu.class))).thenReturn(1);

        // When
        menuService.unfavoriteMenu(1L, 1L);

        // Then
        verify(menuMapper).updateById(argThat(menu ->
            menu.getIsFavorite() == 0));
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
            .thenReturn(5L) // 想去
            .thenReturn(3L) // 去过
            .thenReturn(2L); // 种草

        // When
        Object result = menuService.getMenuStats(1L);

        // Then
        assertNotNull(result);
        // 验证返回对象包含统计数据
    }

    @Test
    @DisplayName("菜单状态名称转换-想去")
    void menuStatusName_Want_ShouldReturn想去() {
        // Given
        testMenu.setStatus(0);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

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
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

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
        when(menuMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testMenu));

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
        assertNotNull(result.getCreatorName());
        assertEquals("小明", result.getCreatorName());
    }
}
