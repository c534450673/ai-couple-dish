package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.OrderDTO;
import com.aicoupledish.domain.req.CreateOrderReq;
import com.aicoupledish.service.impl.OrderServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 订单服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("订单服务测试")
class OrderServiceTest {

    @Mock
    private OrderMapper orderMapper;

    @Mock
    private RecipeMapper recipeMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @InjectMocks
    private OrderServiceImpl orderService;

    private Long buyerId;
    private Long sellerId;
    private Long coupleId;
    private User buyer;
    private User seller;
    private Couple couple;
    private Recipe recipe;
    private Order order;

    @BeforeEach
    void setUp() throws Exception {
        buyerId = 1L;
        sellerId = 2L;
        coupleId = 100L;

        // 设置@Value字段
        java.lang.reflect.Field priceField = OrderServiceImpl.class.getDeclaredField("recipeUnitPrice");
        priceField.setAccessible(true);
        priceField.set(orderService, BigDecimal.valueOf(9.9));

        buyer = new User();
        buyer.setId(buyerId);
        buyer.setNickName("买家");
        buyer.setAvatarUrl("/avatar/1.png");

        seller = new User();
        seller.setId(sellerId);
        seller.setNickName("卖家");
        seller.setAvatarUrl("/avatar/2.png");

        couple = new Couple();
        couple.setId(coupleId);
        couple.setUser1Id(buyerId);
        couple.setUser2Id(sellerId);
        couple.setStatus(1);

        recipe = new Recipe();
        recipe.setId(10L);
        recipe.setUserId(sellerId);
        recipe.setTitle("红烧肉");
        recipe.setCoverUrl("/cover/1.png");
        recipe.setStatus(1);
        recipe.setIsDeleted(0);

        order = new Order();
        order.setId(1L);
        order.setCoupleId(coupleId);
        order.setBuyerId(buyerId);
        order.setSellerId(sellerId);
        order.setRecipeId(10L);
        order.setRecipeName("红烧肉");
        order.setQuantity(1);
        order.setTotalAmount(BigDecimal.valueOf(9.9));
        order.setStatus(0); // PENDING
        order.setCreateTime(LocalDateTime.now());
    }

    @Nested
    @DisplayName("创建订单")
    class CreateOrder {

        @Test
        @DisplayName("创建订单-成功")
        void createOrder_success() {
            // Given
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(10L);
            req.setQuantity(2);
            req.setAddress("北京市朝阳区");

            when(recipeMapper.selectById(10L)).thenReturn(recipe);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(couple));
            when(orderMapper.insert(any(Order.class))).thenAnswer(invocation -> {
                Order o = invocation.getArgument(0);
                o.setId(1L); // Simulate MyBatis-Plus setting generated ID
                return 1;
            });

            // When
            Long result = orderService.createOrder(buyerId, req);

            // Then
            assertNotNull(result);
            verify(orderMapper).insert(argThat(o ->
                    o.getBuyerId().equals(buyerId) &&
                    o.getSellerId().equals(sellerId) &&
                    o.getQuantity() == 2 &&
                    o.getTotalAmount().compareTo(BigDecimal.valueOf(19.8)) == 0 &&
                    o.getStatus() == 0
            ));
        }

        @Test
        @DisplayName("创建订单-菜谱不存在应抛异常")
        void createOrder_recipeNotFound_throw() {
            // Given
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(99L);

            when(recipeMapper.selectById(99L)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.createOrder(buyerId, req));
            assertEquals("菜谱不存在", ex.getMessage());
        }

        @Test
        @DisplayName("创建订单-菜谱已删除应抛异常")
        void createOrder_recipeDeleted_throw() {
            // Given
            recipe.setIsDeleted(1);
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(10L);

            when(recipeMapper.selectById(10L)).thenReturn(recipe);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.createOrder(buyerId, req));
            assertEquals("菜谱不存在", ex.getMessage());
        }

        @Test
        @DisplayName("创建订单-菜谱未发布应抛异常")
        void createOrder_recipeNotPublished_throw() {
            // Given
            recipe.setStatus(0);
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(10L);

            when(recipeMapper.selectById(10L)).thenReturn(recipe);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.createOrder(buyerId, req));
            assertEquals("菜谱未发布", ex.getMessage());
        }

        @Test
        @DisplayName("创建订单-不能购买自己的菜谱应抛异常")
        void createOrder_selfRecipe_throw() {
            // Given
            recipe.setUserId(buyerId); // buyer's own recipe
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(10L);

            when(recipeMapper.selectById(10L)).thenReturn(recipe);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.createOrder(buyerId, req));
            assertEquals("不能购买自己的菜谱", ex.getMessage());
        }

        @Test
        @DisplayName("创建订单-只能购买伴侣的菜谱应抛异常")
        void createOrder_notPartner_throw() {
            // Given
            recipe.setUserId(999L); // recipe by someone else
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(10L);

            when(recipeMapper.selectById(10L)).thenReturn(recipe);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(couple));

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.createOrder(buyerId, req));
            assertEquals("只能购买伴侣的菜谱", ex.getMessage());
        }

        @Test
        @DisplayName("创建订单-未绑定情侣应抛异常")
        void createOrder_notBound_throw() {
            // Given
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(10L);

            when(recipeMapper.selectById(10L)).thenReturn(recipe);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.createOrder(buyerId, req));
            assertEquals("您还没有绑定情侣", ex.getMessage());
        }

        @Test
        @DisplayName("创建订单-默认数量为1")
        void createOrder_defaultQuantity() {
            // Given
            CreateOrderReq req = new CreateOrderReq();
            req.setRecipeId(10L);
            // quantity is null

            when(recipeMapper.selectById(10L)).thenReturn(recipe);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(couple));
            when(orderMapper.insert(any(Order.class))).thenReturn(1);

            // When
            orderService.createOrder(buyerId, req);

            // Then
            verify(orderMapper).insert(argThat(o ->
                    o.getQuantity() == 1 &&
                    o.getTotalAmount().compareTo(BigDecimal.valueOf(9.9)) == 0
            ));
        }
    }

    @Nested
    @DisplayName("取消订单")
    class CancelOrder {

        @Test
        @DisplayName("取消订单-成功")
        void cancelOrder_success() {
            // Given
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.cancelOrder(buyerId, 1L);

            // Then
            verify(orderMapper).updateById(argThat(o -> o.getStatus() == 4));
        }

        @Test
        @DisplayName("取消订单-无权取消应抛异常")
        void cancelOrder_noPermission_throw() {
            // Given
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then - seller tries to cancel
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.cancelOrder(sellerId, 1L));
            assertEquals("无权取消该订单", ex.getMessage());
        }

        @Test
        @DisplayName("取消订单-状态不允许取消应抛异常")
        void cancelOrder_wrongStatus_throw() {
            // Given
            order.setStatus(1); // COOKING
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.cancelOrder(buyerId, 1L));
            assertEquals("订单状态不允许取消", ex.getMessage());
        }

        @Test
        @DisplayName("取消订单-订单不存在应抛异常")
        void cancelOrder_notFound_throw() {
            // Given
            when(orderMapper.selectById(99L)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.cancelOrder(buyerId, 99L));
            assertEquals("订单不存在", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("接单")
    class AcceptOrder {

        @Test
        @DisplayName("接单-成功")
        void acceptOrder_success() {
            // Given
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.acceptOrder(sellerId, 1L);

            // Then
            verify(orderMapper).updateById(argThat(o ->
                    o.getStatus() == 1 && o.getAcceptTime() != null
            ));
        }

        @Test
        @DisplayName("接单-无权接单应抛异常")
        void acceptOrder_noPermission_throw() {
            // Given
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then - buyer tries to accept
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.acceptOrder(buyerId, 1L));
            assertEquals("无权接单", ex.getMessage());
        }

        @Test
        @DisplayName("接单-状态不允许应抛异常")
        void acceptOrder_wrongStatus_throw() {
            // Given
            order.setStatus(1); // already COOKING
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.acceptOrder(sellerId, 1L));
            assertEquals("订单状态不允许接单", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("开始制作")
    class StartCooking {

        @Test
        @DisplayName("开始制作-成功")
        void startCooking_success() {
            // Given
            order.setStatus(1); // COOKING
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When
            orderService.startCooking(sellerId, 1L);

            // Then - no exception means success
        }

        @Test
        @DisplayName("开始制作-状态不正确应抛异常")
        void startCooking_wrongStatus_throw() {
            // Given
            order.setStatus(0); // PENDING
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.startCooking(sellerId, 1L));
            assertEquals("订单状态不正确，当前状态不允许开始制作", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("完成制作")
    class FinishCooking {

        @Test
        @DisplayName("完成制作-成功")
        void finishCooking_success() {
            // Given
            order.setStatus(1); // COOKING
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.finishCooking(sellerId, 1L);

            // Then
            verify(orderMapper).updateById(argThat(o -> o.getStatus() == 2));
        }

        @Test
        @DisplayName("完成制作-状态不允许应抛异常")
        void finishCooking_wrongStatus_throw() {
            // Given
            order.setStatus(0); // PENDING
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.finishCooking(sellerId, 1L));
            assertEquals("订单状态不允许完成制作", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("确认完成订单")
    class CompleteOrder {

        @Test
        @DisplayName("确认完成-买家确认成功")
        void completeOrder_buyerConfirm_success() {
            // Given
            order.setStatus(2); // WAITING_DELIVERY
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.completeOrder(buyerId, 1L);

            // Then
            verify(orderMapper).updateById(argThat(o ->
                    o.getStatus() == 3 && o.getCompleteTime() != null
            ));
        }

        @Test
        @DisplayName("确认完成-卖家确认成功")
        void completeOrder_sellerConfirm_success() {
            // Given
            order.setStatus(2);
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.completeOrder(sellerId, 1L);

            // Then
            verify(orderMapper).updateById(argThat(o -> o.getStatus() == 3));
        }

        @Test
        @DisplayName("确认完成-无权操作应抛异常")
        void completeOrder_noPermission_throw() {
            // Given
            order.setStatus(2);
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then - third party tries
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.completeOrder(999L, 1L));
            assertEquals("无权操作", ex.getMessage());
        }

        @Test
        @DisplayName("确认完成-状态不允许应抛异常")
        void completeOrder_wrongStatus_throw() {
            // Given
            order.setStatus(0); // PENDING
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.completeOrder(buyerId, 1L));
            assertEquals("订单状态不允许确认完成", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("申请退款")
    class ApplyRefund {

        @Test
        @DisplayName("申请退款-待接单状态成功")
        void applyRefund_pending_success() {
            // Given
            order.setStatus(0);
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.applyRefund(buyerId, 1L, "不想吃了");

            // Then
            verify(orderMapper).updateById(argThat(o ->
                    o.getStatus() == 5 && o.getRemark().contains("退款原因")
            ));
        }

        @Test
        @DisplayName("申请退款-制作中状态成功")
        void applyRefund_cooking_success() {
            // Given
            order.setStatus(1);
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.applyRefund(buyerId, 1L, "等太久了");

            // Then
            verify(orderMapper).updateById(argThat(o -> o.getStatus() == 5));
        }

        @Test
        @DisplayName("申请退款-只有买家可以申请")
        void applyRefund_notBuyer_throw() {
            // Given
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.applyRefund(sellerId, 1L, "不想吃了"));
            assertEquals("只有买家可以申请退款", ex.getMessage());
        }

        @Test
        @DisplayName("申请退款-状态不允许应抛异常")
        void applyRefund_wrongStatus_throw() {
            // Given
            order.setStatus(3); // COMPLETED
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.applyRefund(buyerId, 1L, "不想吃了"));
            assertEquals("订单状态不允许退款", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("确认退款")
    class ConfirmRefund {

        @Test
        @DisplayName("确认退款-成功")
        void confirmRefund_success() {
            // Given
            order.setStatus(5); // REFUNDING
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(orderMapper.updateById(any(Order.class))).thenReturn(1);

            // When
            orderService.confirmRefund(sellerId, 1L);

            // Then
            verify(orderMapper).updateById(argThat(o -> o.getStatus() == 6));
        }

        @Test
        @DisplayName("确认退款-只有卖家可以确认")
        void confirmRefund_notSeller_throw() {
            // Given
            order.setStatus(5);
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.confirmRefund(buyerId, 1L));
            assertEquals("只有卖家可以确认退款", ex.getMessage());
        }

        @Test
        @DisplayName("确认退款-状态不正确应抛异常")
        void confirmRefund_wrongStatus_throw() {
            // Given
            order.setStatus(0);
            when(orderMapper.selectById(1L)).thenReturn(order);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.confirmRefund(sellerId, 1L));
            assertEquals("订单状态不正确", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("获取订单详情")
    class GetOrderDetail {

        @Test
        @DisplayName("获取订单详情-成功")
        void getOrderDetail_success() {
            // Given
            when(orderMapper.selectById(1L)).thenReturn(order);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(couple));
            when(userMapper.selectBatchIds(any())).thenReturn(List.of(buyer, seller));
            when(recipeMapper.selectById(10L)).thenReturn(recipe);

            // When
            OrderDTO result = orderService.getOrderDetail(buyerId, 1L);

            // Then
            assertNotNull(result);
            assertEquals(order.getId(), result.getId());
            assertEquals("待接单", result.getStatusDesc());
        }

        @Test
        @DisplayName("获取订单详情-无权查看应抛异常")
        void getOrderDetail_noPermission_throw() {
            // Given
            Couple otherCouple = new Couple();
            otherCouple.setId(999L);
            otherCouple.setUser1Id(10L);
            otherCouple.setUser2Id(20L);
            otherCouple.setStatus(1);

            when(orderMapper.selectById(1L)).thenReturn(order);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(otherCouple));

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> orderService.getOrderDetail(buyerId, 1L));
            assertEquals("无权查看该订单", ex.getMessage());
        }
    }

    @Nested
    @DisplayName("获取待处理订单数")
    class GetPendingOrderCount {

        @Test
        @DisplayName("获取待处理订单数-成功")
        void getPendingOrderCount_success() {
            // Given
            when(orderMapper.selectCount(any(LambdaQueryWrapper.class)))
                    .thenReturn(2L)   // buyer waiting delivery count
                    .thenReturn(3L);  // seller pending/cooking count

            // When
            Integer result = orderService.getPendingOrderCount(buyerId);

            // Then
            assertEquals(5, result);
        }

        @Test
        @DisplayName("获取待处理订单数-无待处理订单")
        void getPendingOrderCount_zero() {
            // Given
            when(orderMapper.selectCount(any(LambdaQueryWrapper.class)))
                    .thenReturn(0L)
                    .thenReturn(0L);

            // When
            Integer result = orderService.getPendingOrderCount(buyerId);

            // Then
            assertEquals(0, result);
        }
    }

    @Nested
    @DisplayName("获取订单列表")
    class GetOrderList {

        @Test
        @DisplayName("获取我购买的订单-成功")
        void getMyBuyOrders_success() {
            // Given
            Page<Order> page = new Page<>(1, 10);
            page.setRecords(List.of(order));
            page.setTotal(1);
            when(orderMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class))).thenReturn(page);
            when(userMapper.selectBatchIds(any())).thenReturn(List.of(buyer, seller));
            when(recipeMapper.selectBatchIds(any())).thenReturn(List.of(recipe));

            // When
            Page<OrderDTO> result = orderService.getMyBuyOrders(buyerId, null, 1, 10);

            // Then
            assertNotNull(result);
            assertEquals(1, result.getTotal());
        }

        @Test
        @DisplayName("获取我出售的订单-成功")
        void getMySellOrders_success() {
            // Given
            Page<Order> page = new Page<>(1, 10);
            page.setRecords(List.of(order));
            page.setTotal(1);
            when(orderMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class))).thenReturn(page);
            when(userMapper.selectBatchIds(any())).thenReturn(List.of(buyer, seller));
            when(recipeMapper.selectBatchIds(any())).thenReturn(List.of(recipe));

            // When
            Page<OrderDTO> result = orderService.getMySellOrders(sellerId, null, 1, 10);

            // Then
            assertNotNull(result);
            assertEquals(1, result.getTotal());
        }

        @Test
        @DisplayName("获取情侣订单-成功")
        void getCoupleOrders_success() {
            // Given
            Page<Order> page = new Page<>(1, 10);
            page.setRecords(List.of(order));
            page.setTotal(1);
            when(coupleMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(couple));
            when(orderMapper.selectPage(any(Page.class), any(LambdaQueryWrapper.class))).thenReturn(page);
            when(userMapper.selectBatchIds(any())).thenReturn(List.of(buyer, seller));
            when(recipeMapper.selectBatchIds(any())).thenReturn(List.of(recipe));

            // When
            Page<OrderDTO> result = orderService.getCoupleOrders(buyerId, null, 1, 10);

            // Then
            assertNotNull(result);
            assertEquals(1, result.getTotal());
        }
    }
}
