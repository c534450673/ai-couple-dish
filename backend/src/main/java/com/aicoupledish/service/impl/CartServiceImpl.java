package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CartMapper;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.OrderMapper;
import com.aicoupledish.dao.mapper.RecipeMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Cart;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.Order;
import com.aicoupledish.dao.model.Recipe;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.CartDTO;
import com.aicoupledish.domain.req.AddToCartReq;
import com.aicoupledish.service.CartService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 购物车服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CartServiceImpl implements CartService {

    private final CartMapper cartMapper;
    private final RecipeMapper recipeMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;
    private final OrderMapper orderMapper;

    /**
     * 固定单价
     */
    private static final BigDecimal UNIT_PRICE = BigDecimal.valueOf(9.9);

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long addToCart(Long userId, AddToCartReq req) {
        // 获取菜谱信息
        Recipe recipe = recipeMapper.selectById(req.getRecipeId());
        if (recipe == null || recipe.getIsDeleted() == 1) {
            throw new BusinessException("菜谱不存在");
        }

        if (recipe.getStatus() != 1) {
            throw new BusinessException("菜谱未发布");
        }

        // 不能添加自己的菜谱
        if (recipe.getUserId().equals(userId)) {
            throw new BusinessException("不能添加自己的菜谱");
        }

        // 验证是伴侣的菜谱
        Couple couple = getCoupleByUserId(userId);
        Long partnerId = getPartnerId(couple, userId);
        if (!recipe.getUserId().equals(partnerId)) {
            throw new BusinessException("只能购买伴侣的菜谱");
        }

        // 检查是否已存在
        Cart existingCart = cartMapper.selectOne(
                new LambdaQueryWrapper<Cart>()
                        .eq(Cart::getUserId, userId)
                        .eq(Cart::getRecipeId, req.getRecipeId())
                        .eq(Cart::getIsDeleted, 0)
        );

        if (existingCart != null) {
            // 更新数量
            int newQuantity = existingCart.getQuantity() + (req.getQuantity() != null ? req.getQuantity() : 1);
            existingCart.setQuantity(newQuantity);
            cartMapper.updateById(existingCart);
            log.info("用户 {} 更新购物车, cartId={}, quantity={}", userId, existingCart.getId(), newQuantity);
            return existingCart.getId();
        }

        // 创建新的购物车记录
        Cart cart = new Cart();
        cart.setUserId(userId);
        cart.setRecipeId(req.getRecipeId());
        cart.setQuantity(req.getQuantity() != null ? req.getQuantity() : 1);
        cart.setIsDeleted(0);

        cartMapper.insert(cart);

        log.info("用户 {} 添加购物车成功, cartId={}", userId, cart.getId());
        return cart.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateQuantity(Long userId, Long cartId, Integer quantity) {
        Cart cart = getCartById(cartId);
        validateCartOwner(cart, userId);

        if (quantity == null || quantity <= 0) {
            throw new BusinessException("数量必须大于0");
        }

        cart.setQuantity(quantity);
        cartMapper.updateById(cart);

        log.info("用户 {} 更新购物车数量, cartId={}, quantity={}", userId, cartId, quantity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void removeFromCart(Long userId, Long cartId) {
        Cart cart = getCartById(cartId);
        validateCartOwner(cart, userId);

        cartMapper.deleteById(cartId);

        log.info("用户 {} 移除购物车项目 {}", userId, cartId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void batchRemove(Long userId, List<Long> cartIds) {
        if (cartIds == null || cartIds.isEmpty()) {
            return;
        }

        // 验证所有购物车项目属于该用户
        List<Cart> carts = cartMapper.selectBatchIds(cartIds);
        for (Cart cart : carts) {
            if (!cart.getUserId().equals(userId)) {
                throw new BusinessException("无权操作部分购物车项目");
            }
        }

        cartMapper.deleteBatchIds(cartIds);

        log.info("用户 {} 批量移除购物车项目 {}", userId, cartIds);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void clearCart(Long userId) {
        cartMapper.delete(
                new LambdaQueryWrapper<Cart>()
                        .eq(Cart::getUserId, userId)
        );

        log.info("用户 {} 清空购物车", userId);
    }

    @Override
    public List<CartDTO> getCartList(Long userId) {
        List<Cart> carts = cartMapper.selectList(
                new LambdaQueryWrapper<Cart>()
                        .eq(Cart::getUserId, userId)
                        .eq(Cart::getIsDeleted, 0)
                        .orderByDesc(Cart::getCreateTime)
        );

        if (carts.isEmpty()) {
            return new ArrayList<>();
        }

        // 批量获取菜谱信息
        Set<Long> recipeIds = carts.stream()
                .map(Cart::getRecipeId)
                .collect(Collectors.toSet());
        Map<Long, Recipe> recipeMap = getRecipeMap(recipeIds);

        // 批量获取卖家信息
        Set<Long> sellerIds = recipeMap.values().stream()
                .map(Recipe::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> sellerMap = getUserMap(sellerIds);

        return carts.stream()
                .map(cart -> {
                    CartDTO dto = new CartDTO();
                    dto.setId(cart.getId());
                    dto.setRecipeId(cart.getRecipeId());
                    dto.setQuantity(cart.getQuantity());
                    dto.setCreateTime(cart.getCreateTime());
                    dto.setUnitPrice(UNIT_PRICE);
                    dto.setSubtotal(UNIT_PRICE.multiply(BigDecimal.valueOf(cart.getQuantity())));

                    Recipe recipe = recipeMap.get(cart.getRecipeId());
                    if (recipe != null) {
                        dto.setRecipeTitle(recipe.getTitle());
                        dto.setRecipeCoverUrl(recipe.getCoverUrl());
                        dto.setRecipeDescription(recipe.getDescription());
                        dto.setSellerId(recipe.getUserId());

                        User seller = sellerMap.get(recipe.getUserId());
                        if (seller != null) {
                            dto.setSellerName(seller.getNickName());
                            dto.setSellerAvatar(seller.getAvatarUrl());
                        }
                    }

                    return dto;
                })
                .collect(Collectors.toList());
    }

    @Override
    public Integer getCartCount(Long userId) {
        Long count = cartMapper.selectCount(
                new LambdaQueryWrapper<Cart>()
                        .eq(Cart::getUserId, userId)
                        .eq(Cart::getIsDeleted, 0)
        );
        return count != null ? count.intValue() : 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public List<Long> checkout(Long userId, List<Long> cartIds) {
        if (cartIds == null || cartIds.isEmpty()) {
            throw new BusinessException("请选择要结算的商品");
        }

        // 获取购物车项目
        List<Cart> carts = cartMapper.selectBatchIds(cartIds);
        if (carts.isEmpty()) {
            throw new BusinessException("购物车项目不存在");
        }

        // 验证权限
        for (Cart cart : carts) {
            validateCartOwner(cart, userId);
        }

        // 获取情侣信息
        Couple couple = getCoupleByUserId(userId);

        // 获取菜谱信息
        Set<Long> recipeIds = carts.stream()
                .map(Cart::getRecipeId)
                .collect(Collectors.toSet());
        Map<Long, Recipe> recipeMap = getRecipeMap(recipeIds);

        // 创建订单
        List<Long> orderIds = new ArrayList<>();
        for (Cart cart : carts) {
            Recipe recipe = recipeMap.get(cart.getRecipeId());
            if (recipe == null || recipe.getIsDeleted() == 1 || recipe.getStatus() != 1) {
                continue;
            }

            BigDecimal totalAmount = UNIT_PRICE.multiply(BigDecimal.valueOf(cart.getQuantity()));

            Order order = new Order();
            order.setCoupleId(couple.getId());
            order.setBuyerId(userId);
            order.setSellerId(recipe.getUserId());
            order.setRecipeId(recipe.getId());
            order.setRecipeName(recipe.getTitle());
            order.setQuantity(cart.getQuantity());
            order.setTotalAmount(totalAmount);
            order.setStatus(0); // 待接单

            orderMapper.insert(order);
            orderIds.add(order.getId());
        }

        // 删除已结算的购物车项目
        cartMapper.deleteBatchIds(cartIds);

        log.info("用户 {} 结算购物车, 创建订单 {}", userId, orderIds);
        return orderIds;
    }

    /**
     * 根据ID获取购物车项目
     */
    private Cart getCartById(Long cartId) {
        Cart cart = cartMapper.selectById(cartId);
        if (cart == null || cart.getIsDeleted() == 1) {
            throw new BusinessException("购物车项目不存在");
        }
        return cart;
    }

    /**
     * 验证购物车所有者
     */
    private void validateCartOwner(Cart cart, Long userId) {
        if (!cart.getUserId().equals(userId)) {
            throw new BusinessException("无权操作该购物车项目");
        }
    }

    /**
     * 获取用户的情侣信息
     */
    private Couple getCoupleByUserId(Long userId) {
        List<Couple> couples = coupleMapper.selectList(
                new LambdaQueryWrapper<Couple>()
                        .eq(Couple::getStatus, 1)
                        .and(wrapper -> wrapper
                                .eq(Couple::getUser1Id, userId)
                                .or()
                                .eq(Couple::getUser2Id, userId))
                        .last("LIMIT 1")
        );
        if (couples.isEmpty()) {
            throw new BusinessException("您还没有绑定情侣");
        }
        return couples.get(0);
    }

    /**
     * 获取伙伴ID
     */
    private Long getPartnerId(Couple couple, Long userId) {
        return couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();
    }

    /**
     * 批量获取用户信息
     */
    private Map<Long, User> getUserMap(Set<Long> userIds) {
        if (userIds == null || userIds.isEmpty()) {
            return Collections.emptyMap();
        }
        List<User> users = userMapper.selectBatchIds(userIds);
        return users.stream().collect(Collectors.toMap(User::getId, u -> u, (a, b) -> a));
    }

    /**
     * 批量获取菜谱信息
     */
    private Map<Long, Recipe> getRecipeMap(Set<Long> recipeIds) {
        if (recipeIds == null || recipeIds.isEmpty()) {
            return Collections.emptyMap();
        }
        List<Recipe> recipes = recipeMapper.selectBatchIds(recipeIds);
        return recipes.stream().collect(Collectors.toMap(Recipe::getId, r -> r, (a, b) -> a));
    }
}
