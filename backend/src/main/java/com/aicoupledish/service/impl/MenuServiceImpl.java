package com.aicoupledish.service.impl;

import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMenuMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.CoupleMenu;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.MenuDTO;
import com.aicoupledish.domain.dto.PageDTO;
import com.aicoupledish.domain.req.AddMenuReq;
import com.aicoupledish.service.MenuService;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 菜单服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MenuServiceImpl implements MenuService {

    private final CoupleMenuMapper menuMapper;
    private final UserMapper userMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    @Override
    public PageDTO<MenuDTO> getMenuList(Long userId, Integer status, String keyword, String dishCategory,
                                          BigDecimal minPrice, BigDecimal maxPrice, Integer minRating,
                                          String sortBy, String sortOrder, Long page, Long pageSize) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 设置默认值
        page = page != null && page > 0 ? page : 1L;
        pageSize = pageSize != null && pageSize > 0 ? pageSize : 10L;
        sortBy = StrUtil.isBlank(sortBy) ? "time" : sortBy;
        sortOrder = StrUtil.isBlank(sortOrder) ? "desc" : sortOrder;

        LambdaQueryWrapper<CoupleMenu> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(CoupleMenu::getCoupleId, user.getCoupleId());
        queryWrapper.eq(status != null, CoupleMenu::getStatus, status);
        queryWrapper.like(StrUtil.isNotBlank(keyword), CoupleMenu::getRestaurantName, keyword);
        queryWrapper.eq(StrUtil.isNotBlank(dishCategory), CoupleMenu::getDishCategory, dishCategory);
        queryWrapper.ge(minPrice != null, CoupleMenu::getPrice, minPrice);
        queryWrapper.le(maxPrice != null, CoupleMenu::getPrice, maxPrice);
        queryWrapper.ge(minRating != null, CoupleMenu::getRating, minRating);

        // 排序
        if ("rating".equals(sortBy)) {
            if ("asc".equals(sortOrder)) {
                queryWrapper.orderByAsc(CoupleMenu::getRating);
            } else {
                queryWrapper.orderByDesc(CoupleMenu::getRating);
            }
        } else if ("likeCount".equals(sortBy)) {
            if ("asc".equals(sortOrder)) {
                queryWrapper.orderByAsc(CoupleMenu::getLikeCount);
            } else {
                queryWrapper.orderByDesc(CoupleMenu::getLikeCount);
            }
        } else {
            if ("asc".equals(sortOrder)) {
                queryWrapper.orderByAsc(CoupleMenu::getCreateTime);
            } else {
                queryWrapper.orderByDesc(CoupleMenu::getCreateTime);
            }
        }

        // 分页查询
        Page<CoupleMenu> pageParam = new Page<>(page, pageSize);
        Page<CoupleMenu> pageResult = menuMapper.selectPage(pageParam, queryWrapper);

        List<MenuDTO> dtoList = buildMenuDTOList(pageResult.getRecords());

        return PageDTO.of(dtoList, page, pageSize, pageResult.getTotal());
    }

    @Override
    public MenuDTO getMenuDetail(Long userId, Long menuId) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);

        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        return buildMenuDTO(menu);
    }

    @Override
    @Transactional
    public Long addMenu(Long userId, AddMenuReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleMenu menu = new CoupleMenu();
        menu.setCoupleId(user.getCoupleId());
        menu.setCreatorId(userId);
        menu.setRestaurantName(req.getRestaurantName());
        menu.setDishName(req.getDishName());
        menu.setDishCategory(req.getDishCategory());
        menu.setPrice(req.getPrice());
        menu.setLocation(req.getLocation());
        menu.setLatitude(req.getLatitude());
        menu.setLongitude(req.getLongitude());
        menu.setNote(req.getNote());
        menu.setRating(req.getRating());
        menu.setStatus(req.getStatus() != null ? req.getStatus() : 0);

        if (req.getEaterIds() != null && !req.getEaterIds().isEmpty()) {
            menu.setEaterIds(JSONUtil.toJsonStr(req.getEaterIds()));
        }

        menu.setEatenDate(req.getEatenDate() != null ? LocalDate.parse(req.getEatenDate()) : null);

        menuMapper.insert(menu);
        log.info("添加菜单: userId={}, menuId={}", userId, menu.getId());

        return menu.getId();
    }

    @Override
    @Transactional
    public void updateMenu(Long userId, Long menuId, AddMenuReq req) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);

        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        menu.setRestaurantName(req.getRestaurantName());
        menu.setDishName(req.getDishName());
        menu.setDishCategory(req.getDishCategory());
        menu.setPrice(req.getPrice());
        menu.setLocation(req.getLocation());
        menu.setLatitude(req.getLatitude());
        menu.setLongitude(req.getLongitude());
        menu.setNote(req.getNote());
        menu.setRating(req.getRating());

        if (req.getStatus() != null) {
            menu.setStatus(req.getStatus());
        }

        if (req.getEaterIds() != null) {
            menu.setEaterIds(JSONUtil.toJsonStr(req.getEaterIds()));
        }

        menu.setEatenDate(req.getEatenDate() != null ? LocalDate.parse(req.getEatenDate()) : null);

        menuMapper.updateById(menu);
        log.info("更新菜单: userId={}, menuId={}", userId, menuId);
    }

    @Override
    @Transactional
    public void deleteMenu(Long userId, Long menuId) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);

        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        menu.setIsDeleted(1);
        menu.setDeleteTime(LocalDateTime.now());
        menuMapper.updateById(menu);
        log.info("删除菜单: userId={}, menuId={}", userId, menuId);
    }

    @Override
    @Transactional
    public void recoverMenu(Long userId, Long menuId) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);

        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        menu.setIsDeleted(0);
        menu.setDeleteTime(null);
        menuMapper.updateById(menu);
        log.info("恢复菜单: userId={}, menuId={}", userId, menuId);
    }

    @Override
    @Transactional
    public void likeMenu(Long userId, Long menuId) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);
        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        // 权限检查：确保用户属于该菜单的情侣关系
        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        // 使用原子更新避免竞态条件
        menuMapper.update(null, new LambdaUpdateWrapper<CoupleMenu>()
                .eq(CoupleMenu::getId, menuId)
                .setSql("like_count = like_count + 1"));
    }

    @Override
    @Transactional
    public void unlikeMenu(Long userId, Long menuId) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);
        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        // 权限检查：确保用户属于该菜单的情侣关系
        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        // 使用原子更新避免竞态条件，确保不会变成负数
        menuMapper.update(null, new LambdaUpdateWrapper<CoupleMenu>()
                .eq(CoupleMenu::getId, menuId)
                .gt(CoupleMenu::getLikeCount, 0)
                .setSql("like_count = like_count - 1"));
    }

    @Override
    @Transactional
    public void favoriteMenu(Long userId, Long menuId) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);
        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        // 权限检查：确保用户属于该菜单的情侣关系
        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        menu.setIsFavorite(1);
        menuMapper.updateById(menu);
    }

    @Override
    @Transactional
    public void unfavoriteMenu(Long userId, Long menuId) {
        User user = getUserById(userId);
        CoupleMenu menu = menuMapper.selectById(menuId);
        if (menu == null) {
            throw BusinessException.MENU_NOT_FOUND;
        }

        // 权限检查：确保用户属于该菜单的情侣关系
        if (!menu.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.MENU_NOT_PERMISSION;
        }

        menu.setIsFavorite(0);
        menuMapper.updateById(menu);
    }

    @Override
    public Object getMenuStats(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        Map<String, Object> stats = new HashMap<>();

        // 总数量
        Long totalCount = menuMapper.selectCount(
            new LambdaQueryWrapper<CoupleMenu>()
                .eq(CoupleMenu::getCoupleId, user.getCoupleId())
                .eq(CoupleMenu::getIsDeleted, 0)
        );
        stats.put("totalCount", totalCount != null ? totalCount : 0L);

        // 想去数量
        Long wantToGoCount = menuMapper.selectCount(
            new LambdaQueryWrapper<CoupleMenu>()
                .eq(CoupleMenu::getCoupleId, user.getCoupleId())
                .eq(CoupleMenu::getStatus, 0)
                .eq(CoupleMenu::getIsDeleted, 0)
        );
        stats.put("wantToGoCount", wantToGoCount != null ? wantToGoCount : 0L);

        // 去过数量
        Long visitedCount = menuMapper.selectCount(
            new LambdaQueryWrapper<CoupleMenu>()
                .eq(CoupleMenu::getCoupleId, user.getCoupleId())
                .eq(CoupleMenu::getStatus, 1)
                .eq(CoupleMenu::getIsDeleted, 0)
        );
        stats.put("visitedCount", visitedCount != null ? visitedCount : 0L);

        // 种草数量
        Long seededCount = menuMapper.selectCount(
            new LambdaQueryWrapper<CoupleMenu>()
                .eq(CoupleMenu::getCoupleId, user.getCoupleId())
                .eq(CoupleMenu::getStatus, 2)
                .eq(CoupleMenu::getIsDeleted, 0)
        );
        stats.put("seededCount", seededCount != null ? seededCount : 0L);

        return stats;
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private List<MenuDTO> buildMenuDTOList(List<CoupleMenu> menus) {
        if (menus == null || menus.isEmpty()) {
            return new ArrayList<>();
        }
        return menus.stream().map(this::buildMenuDTO).collect(Collectors.toList());
    }

    private MenuDTO buildMenuDTO(CoupleMenu menu) {
        MenuDTO dto = new MenuDTO();
        dto.setId(menu.getId());
        dto.setRestaurantName(menu.getRestaurantName());
        dto.setDishName(menu.getDishName());
        dto.setDishCategory(menu.getDishCategory());
        dto.setPrice(menu.getPrice());
        dto.setLocation(menu.getLocation());
        dto.setLatitude(menu.getLatitude());
        dto.setLongitude(menu.getLongitude());
        dto.setNote(menu.getNote());
        dto.setRating(menu.getRating());
        dto.setStatus(menu.getStatus());
        dto.setStatusName(getStatusName(menu.getStatus()));
        dto.setLikeCount(menu.getLikeCount());
        dto.setIsFavorite(menu.getIsFavorite() == 1);
        dto.setCreateTime(menu.getCreateTime() != null ? menu.getCreateTime().toString() : null);

        if (StrUtil.isNotBlank(menu.getEaterIds())) {
            dto.setEaterIds(JSONUtil.toList(menu.getEaterIds(), Long.class));
        }

        return dto;
    }

    private String getStatusName(Integer status) {
        if (status == null) return "未知";
        switch (status) {
            case 0: return "想去";
            case 1: return "去过";
            case 2: return "种草";
            default: return "未知";
        }
    }
}
