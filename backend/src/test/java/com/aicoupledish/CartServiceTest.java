package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.CartDTO;
import com.aicoupledish.domain.req.AddToCartReq;
import com.aicoupledish.service.impl.CartServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 购物车服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("购物车服务测试")
class CartServiceTest {

    @Mock
    private CartMapper cartMapper;

    @Mock
    private RecipeMapper recipeMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private OrderMapper orderMapper;

    @InjectMocks
    private CartServiceImpl cartService;

    private Long userId;
    private Long partnerId;
    private Long coupleId;
    private Recipe recipe;
    private Couple couple;
    private User user;
    private User partner;

    @BeforeEach
    void setUp() {
        userId = 1L;
        partnerId = 2L;
        coupleId = 100L;

        user = new User();
        user.setId(userId);
        user.setNickName("小明");
        user.setAvatarUrl("/avatar/1.png");

        partner = new User();
        partner.setId(partnerId);
        partner.setNickName("小红");
        partner.setAvatarUrl("/avatar/2.png");

        couple = new Couple();
        couple.setId(coupleId);
        couple.setUser1Id(userId);
        couple.setUser2Id(partnerId);
        couple.setStatus(1);

        recipe = new Recipe();
        recipe.setId(10L);
        recipe.setUserId(partnerId);
        recipe.setTitle("红烧肉");
        recipe.setCoverUrl("/cover/10.png");
        recipe.setDescription("美味红烧肉");
        recipe.setStatus(1);
        recipe.setIsDeleted(0);
    }

    private void mockGetCoupleByUserId() {
        when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                .thenReturn(Collections.singletonList(couple));
    }

    @Nested
    @DisplayName("添加购物车")
    class AddToCartTest {

        @Test
        @DisplayName("添加购物车-成功-新建购物车项")
        void addToCart_Success_NewItem() {
            // Given
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());
            req.setQuantity(2);

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);
            mockGetCoupleByUserId();
            when(cartMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(cartMapper.insert(any(Cart.class))).thenAnswer(invocation -> {
                Cart cart = invocation.getArgument(0);
                cart.setId(1L);
                return 1;
            });

            // When
            Long cartId = cartService.addToCart(userId, req);

            // Then
            assertNotNull(cartId);
            assertEquals(1L, cartId);
            verify(cartMapper).insert(argThat(cart ->
                    cart.getUserId().equals(userId) &&
                    cart.getRecipeId().equals(recipe.getId()) &&
                    cart.getQuantity() == 2
            ));
        }

        @Test
        @DisplayName("添加购物车-成功-已存在则更新数量")
        void addToCart_Success_UpdateExisting() {
            // Given
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());
            req.setQuantity(3);

            Cart existingCart = new Cart();
            existingCart.setId(5L);
            existingCart.setUserId(userId);
            existingCart.setRecipeId(recipe.getId());
            existingCart.setQuantity(2);

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);
            mockGetCoupleByUserId();
            when(cartMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingCart);

            // When
            Long cartId = cartService.addToCart(userId, req);

            // Then
            assertEquals(5L, cartId);
            verify(cartMapper).updateById(argThat(cart -> cart.getQuantity() == 5));
        }

        @Test
        @DisplayName("添加购物车-菜谱不存在应抛异常")
        void addToCart_RecipeNotFound() {
            // Given
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(999L);

            when(recipeMapper.selectById(999L)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.addToCart(userId, req));
            assertEquals("菜谱不存在", ex.getMessage());
        }

        @Test
        @DisplayName("添加购物车-菜谱已删除应抛异常")
        void addToCart_RecipeDeleted() {
            // Given
            recipe.setIsDeleted(1);
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.addToCart(userId, req));
            assertEquals("菜谱不存在", ex.getMessage());
        }

        @Test
        @DisplayName("添加购物车-菜谱未发布应抛异常")
        void addToCart_RecipeNotPublished() {
            // Given
            recipe.setStatus(0);
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.addToCart(userId, req));
            assertEquals("菜谱未发布", ex.getMessage());
        }

        @Test
        @DisplayName("添加购物车-不能添加自己的菜谱")
        void addToCart_CannotAddOwnRecipe() {
            // Given
            recipe.setUserId(userId);
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.addToCart(userId, req));
            assertEquals("不能添加自己的菜谱", ex.getMessage());
        }

        @Test
        @DisplayName("添加购物车-只能购买伴侣的菜谱")
        void addToCart_OnlyPartnerRecipe() {
            // Given
            recipe.setUserId(999L); // 第三方用户
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);
            mockGetCoupleByUserId();

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.addToCart(userId, req));
            assertEquals("只能购买伴侣的菜谱", ex.getMessage());
        }

        @Test
        @DisplayName("添加购物车-未绑定情侣应抛异常")
        void addToCart_CoupleNotBound() {
            // Given
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.addToCart(userId, req));
            assertEquals("您还没有绑定情侣", ex.getMessage());
        }

        @Test
        @DisplayName("添加购物车-数量为空时默认为1")
        void addToCart_DefaultQuantity() {
            // Given
            AddToCartReq req = new AddToCartReq();
            req.setRecipeId(recipe.getId());
            req.setQuantity(null);

            when(recipeMapper.selectById(recipe.getId())).thenReturn(recipe);
            mockGetCoupleByUserId();
            when(cartMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(cartMapper.insert(any(Cart.class))).thenAnswer(invocation -> {
                Cart cart = invocation.getArgument(0);
                cart.setId(1L);
                return 1;
            });

            // When
            cartService.addToCart(userId, req);

            // Then
            verify(cartMapper).insert(argThat(cart -> cart.getQuantity() == 1));
        }
    }

    @Nested
    @DisplayName("更新购物车数量")
    class UpdateQuantityTest {

        @Test
        @DisplayName("更新数量-成功")
        void updateQuantity_Success() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(userId);
            cart.setQuantity(2);
            cart.setIsDeleted(0);

            when(cartMapper.selectById(1L)).thenReturn(cart);

            // When
            cartService.updateQuantity(userId, 1L, 5);

            // Then
            verify(cartMapper).updateById(argThat(c -> c.getQuantity() == 5));
        }

        @Test
        @DisplayName("更新数量-购物车项不存在应抛异常")
        void updateQuantity_CartNotFound() {
            // Given
            when(cartMapper.selectById(999L)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.updateQuantity(userId, 999L, 5));
            assertEquals("购物车项目不存在", ex.getMessage());
        }

        @Test
        @DisplayName("更新数量-无权操作他人购物车")
        void updateQuantity_NotOwner() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(999L);
            cart.setIsDeleted(0);

            when(cartMapper.selectById(1L)).thenReturn(cart);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.updateQuantity(userId, 1L, 5));
            assertEquals("无权操作该购物车项目", ex.getMessage());
        }

        @Test
        @DisplayName("更新数量-数量必须大于0")
        void updateQuantity_InvalidQuantity() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(userId);
            cart.setIsDeleted(0);

            when(cartMapper.selectById(1L)).thenReturn(cart);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.updateQuantity(userId, 1L, 0));
            assertEquals("数量必须大于0", ex.getMessage());
        }

        @Test
        @DisplayName("更新数量-数量为null应抛异常")
        void updateQuantity_NullQuantity() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(userId);
            cart.setIsDeleted(0);

            when(cartMapper.selectById(1L)).thenReturn(cart);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.updateQuantity(userId, 1L, null));
            assertEquals("数量必须大于0", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("移除购物车")
    class RemoveFromCartTest {

        @Test
        @DisplayName("移除购物车-成功")
        void removeFromCart_Success() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(userId);
            cart.setIsDeleted(0);

            when(cartMapper.selectById(1L)).thenReturn(cart);

            // When
            cartService.removeFromCart(userId, 1L);

            // Then
            verify(cartMapper).deleteById(1L);
        }

        @Test
        @DisplayName("移除购物车-无权操作应抛异常")
        void removeFromCart_NotOwner() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(999L);
            cart.setIsDeleted(0);

            when(cartMapper.selectById(1L)).thenReturn(cart);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.removeFromCart(userId, 1L));
            assertEquals("无权操作该购物车项目", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("批量移除购物车")
    class BatchRemoveTest {

        @Test
        @DisplayName("批量移除-成功")
        void batchRemove_Success() {
            // Given
            Cart cart1 = new Cart();
            cart1.setId(1L);
            cart1.setUserId(userId);
            Cart cart2 = new Cart();
            cart2.setId(2L);
            cart2.setUserId(userId);

            when(cartMapper.selectBatchIds(Arrays.asList(1L, 2L)))
                    .thenReturn(Arrays.asList(cart1, cart2));

            // When
            cartService.batchRemove(userId, Arrays.asList(1L, 2L));

            // Then
            verify(cartMapper).deleteBatchIds(Arrays.asList(1L, 2L));
        }

        @Test
        @DisplayName("批量移除-空列表不执行操作")
        void batchRemove_EmptyList() {
            // When
            cartService.batchRemove(userId, Collections.emptyList());

            // Then
            verify(cartMapper, never()).deleteBatchIds(anyList());
        }

        @Test
        @DisplayName("批量移除-包含非本人项目应抛异常")
        void batchRemove_NotAllOwner() {
            // Given
            Cart cart1 = new Cart();
            cart1.setId(1L);
            cart1.setUserId(userId);
            Cart cart2 = new Cart();
            cart2.setId(2L);
            cart2.setUserId(999L);

            when(cartMapper.selectBatchIds(Arrays.asList(1L, 2L)))
                    .thenReturn(Arrays.asList(cart1, cart2));

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.batchRemove(userId, Arrays.asList(1L, 2L)));
            assertEquals("无权操作部分购物车项目", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("获取购物车列表")
    class GetCartListTest {

        @Test
        @DisplayName("获取购物车列表-成功")
        void getCartList_Success() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(userId);
            cart.setRecipeId(recipe.getId());
            cart.setQuantity(2);
            cart.setCreateTime(java.time.LocalDateTime.now());

            when(cartMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.singletonList(cart));
            when(recipeMapper.selectBatchIds(Collections.singleton(recipe.getId())))
                    .thenReturn(Collections.singletonList(recipe));
            when(userMapper.selectBatchIds(Collections.singleton(partnerId)))
                    .thenReturn(Collections.singletonList(partner));

            // When
            List<CartDTO> result = cartService.getCartList(userId);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            CartDTO dto = result.get(0);
            assertEquals(recipe.getTitle(), dto.getRecipeTitle());
            assertEquals(BigDecimal.valueOf(9.9), dto.getUnitPrice());
            assertEquals(BigDecimal.valueOf(19.8), dto.getSubtotal());
            assertEquals(partner.getNickName(), dto.getSellerName());
        }

        @Test
        @DisplayName("获取购物车列表-空购物车")
        void getCartList_EmptyCart() {
            // Given
            when(cartMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            List<CartDTO> result = cartService.getCartList(userId);

            // Then
            assertNotNull(result);
            assertTrue(result.isEmpty());
        }
    }

    @Nested
    @DisplayName("获取购物车数量")
    class GetCartCountTest {

        @Test
        @DisplayName("获取购物车数量-成功")
        void getCartCount_Success() {
            // Given
            when(cartMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(3L);

            // When
            Integer count = cartService.getCartCount(userId);

            // Then
            assertEquals(3, count);
        }

        @Test
        @DisplayName("获取购物车数量-返回0当null")
        void getCartCount_Null() {
            // Given
            when(cartMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(null);

            // When
            Integer count = cartService.getCartCount(userId);

            // Then
            assertEquals(0, count);
        }
    }

    @Nested
    @DisplayName("结算购物车")
    class CheckoutTest {

        @Test
        @DisplayName("结算-成功创建订单")
        void checkout_Success() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(userId);
            cart.setRecipeId(recipe.getId());
            cart.setQuantity(2);

            when(cartMapper.selectBatchIds(Arrays.asList(1L)))
                    .thenReturn(Collections.singletonList(cart));
            mockGetCoupleByUserId();
            when(recipeMapper.selectBatchIds(Collections.singleton(recipe.getId())))
                    .thenReturn(Collections.singletonList(recipe));
            when(orderMapper.insert(any(Order.class))).thenAnswer(invocation -> {
                Order order = invocation.getArgument(0);
                order.setId(50L);
                return 1;
            });

            // When
            List<Long> orderIds = cartService.checkout(userId, Arrays.asList(1L));

            // Then
            assertNotNull(orderIds);
            assertEquals(1, orderIds.size());
            verify(orderMapper).insert(argThat(order ->
                    order.getBuyerId().equals(userId) &&
                    order.getSellerId().equals(partnerId) &&
                    order.getRecipeId().equals(recipe.getId()) &&
                    order.getStatus() == 0 &&
                    order.getTotalAmount().compareTo(BigDecimal.valueOf(19.8)) == 0
            ));
            verify(cartMapper).deleteBatchIds(Arrays.asList(1L));
        }

        @Test
        @DisplayName("结算-空购物车ID应抛异常")
        void checkout_EmptyCartIds() {
            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.checkout(userId, Collections.emptyList()));
            assertEquals("请选择要结算的商品", ex.getMessage());
        }

        @Test
        @DisplayName("结算-购物车项目不存在应抛异常")
        void checkout_CartNotFound() {
            // Given
            when(cartMapper.selectBatchIds(Arrays.asList(1L)))
                    .thenReturn(Collections.emptyList());

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.checkout(userId, Arrays.asList(1L)));
            assertEquals("购物车项目不存在", ex.getMessage());
        }

        @Test
        @DisplayName("结算-无权操作他人购物车应抛异常")
        void checkout_NotOwner() {
            // Given
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(999L);

            when(cartMapper.selectBatchIds(Arrays.asList(1L)))
                    .thenReturn(Collections.singletonList(cart));

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> cartService.checkout(userId, Arrays.asList(1L)));
            assertEquals("无权操作该购物车项目", ex.getMessage());
        }

        @Test
        @DisplayName("结算-已删除或未发布的菜谱跳过")
        void checkout_SkipInvalidRecipe() {
            // Given
            recipe.setIsDeleted(1);
            Cart cart = new Cart();
            cart.setId(1L);
            cart.setUserId(userId);
            cart.setRecipeId(recipe.getId());
            cart.setQuantity(2);

            when(cartMapper.selectBatchIds(Arrays.asList(1L)))
                    .thenReturn(Collections.singletonList(cart));
            mockGetCoupleByUserId();
            when(recipeMapper.selectBatchIds(Collections.singleton(recipe.getId())))
                    .thenReturn(Collections.singletonList(recipe));

            // When
            List<Long> orderIds = cartService.checkout(userId, Arrays.asList(1L));

            // Then
            assertTrue(orderIds.isEmpty());
            verify(orderMapper, never()).insert(any(Order.class));
        }
    }

    @Nested
    @DisplayName("清空购物车")
    class ClearCartTest {

        @Test
        @DisplayName("清空购物车-成功")
        void clearCart_Success() {
            // When
            cartService.clearCart(userId);

            // Then
            verify(cartMapper).delete(any(LambdaQueryWrapper.class));
        }
    }
}
