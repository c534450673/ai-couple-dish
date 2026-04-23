package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.OrderMapper;
import com.aicoupledish.dao.mapper.RecipeMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.Order;
import com.aicoupledish.dao.model.Recipe;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.OrderDTO;
import com.aicoupledish.domain.req.CreateOrderReq;
import com.aicoupledish.service.OrderService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 订单服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OrderServiceImpl implements OrderService {

    private final OrderMapper orderMapper;
    private final RecipeMapper recipeMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;

    /**
     * 订单状态
     */
    private static final int STATUS_PENDING = 0;        // 待接单
    private static final int STATUS_COOKING = 1;        // 制作中
    private static final int STATUS_WAITING_DELIVERY = 2; // 待送达
    private static final int STATUS_COMPLETED = 3;      // 已完成
    private static final int STATUS_CANCELLED = 4;      // 已取消
    private static final int STATUS_REFUNDING = 5;      // 退款中
    private static final int STATUS_REFUNDED = 6;       // 已退款

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createOrder(Long userId, CreateOrderReq req) {
        // 获取菜谱信息
        Recipe recipe = recipeMapper.selectById(req.getRecipeId());
        if (recipe == null || recipe.getIsDeleted() == 1) {
            throw new BusinessException("菜谱不存在");
        }

        if (recipe.getStatus() != 1) {
            throw new BusinessException("菜谱未发布");
        }

        // 不能购买自己的菜谱
        if (recipe.getUserId().equals(userId)) {
            throw new BusinessException("不能购买自己的菜谱");
        }

        // 获取情侣信息
        Couple couple = getCoupleByUserId(userId);
        Long partnerId = getPartnerId(couple, userId);

        // 验证卖家是伴侣
        if (!recipe.getUserId().equals(partnerId)) {
            throw new BusinessException("只能购买伴侣的菜谱");
        }

        // 计算总价（暂时使用固定价格）
        int quantity = req.getQuantity() != null ? req.getQuantity() : 1;
        BigDecimal unitPrice = BigDecimal.valueOf(9.9); // 固定单价
        BigDecimal totalAmount = unitPrice.multiply(BigDecimal.valueOf(quantity));

        // 创建订单
        Order order = new Order();
        order.setCoupleId(couple.getId());
        order.setBuyerId(userId);
        order.setSellerId(recipe.getUserId());
        order.setRecipeId(recipe.getId());
        order.setRecipeName(recipe.getTitle());
        order.setQuantity(quantity);
        order.setTotalAmount(totalAmount);
        order.setAddress(req.getAddress());
        order.setStatus(STATUS_PENDING);
        order.setRemark(req.getRemark());

        orderMapper.insert(order);

        log.info("用户 {} 创建订单成功, orderId={}", userId, order.getId());
        return order.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void cancelOrder(Long userId, Long orderId) {
        Order order = getOrderById(orderId);

        // 只有买家可以取消
        if (!order.getBuyerId().equals(userId)) {
            throw new BusinessException("无权取消该订单");
        }

        if (order.getStatus() != STATUS_PENDING) {
            throw new BusinessException("订单状态不允许取消");
        }

        order.setStatus(STATUS_CANCELLED);
        order.setCancelTime(LocalDateTime.now());
        orderMapper.updateById(order);

        log.info("用户 {} 取消订单 {}", userId, orderId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void acceptOrder(Long userId, Long orderId) {
        Order order = getOrderById(orderId);

        // 只有卖家可以接单
        if (!order.getSellerId().equals(userId)) {
            throw new BusinessException("无权接单");
        }

        if (order.getStatus() != STATUS_PENDING) {
            throw new BusinessException("订单状态不允许接单");
        }

        order.setStatus(STATUS_COOKING);
        order.setAcceptTime(LocalDateTime.now());
        orderMapper.updateById(order);

        log.info("用户 {} 接单 {}", userId, orderId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void startCooking(Long userId, Long orderId) {
        Order order = getOrderById(orderId);

        if (!order.getSellerId().equals(userId)) {
            throw new BusinessException("无权操作");
        }

        if (order.getStatus() != STATUS_COOKING) {
            throw new BusinessException("订单状态不正确，当前状态不允许开始制作");
        }

        log.info("用户 {} 确认开始制作订单 {}", userId, orderId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void finishCooking(Long userId, Long orderId) {
        Order order = getOrderById(orderId);

        if (!order.getSellerId().equals(userId)) {
            throw new BusinessException("无权操作");
        }

        if (order.getStatus() != STATUS_COOKING) {
            throw new BusinessException("订单状态不允许完成制作");
        }

        order.setStatus(STATUS_WAITING_DELIVERY);
        orderMapper.updateById(order);

        log.info("用户 {} 完成制作订单 {}", userId, orderId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void completeOrder(Long userId, Long orderId) {
        Order order = getOrderById(orderId);

        // 买家或卖家都可以确认完成
        if (!order.getBuyerId().equals(userId) && !order.getSellerId().equals(userId)) {
            throw new BusinessException("无权操作");
        }

        if (order.getStatus() != STATUS_WAITING_DELIVERY) {
            throw new BusinessException("订单状态不允许确认完成");
        }

        order.setStatus(STATUS_COMPLETED);
        order.setCompleteTime(LocalDateTime.now());
        orderMapper.updateById(order);

        log.info("用户 {} 确认完成订单 {}", userId, orderId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void applyRefund(Long userId, Long orderId, String reason) {
        Order order = getOrderById(orderId);

        if (!order.getBuyerId().equals(userId)) {
            throw new BusinessException("只有买家可以申请退款");
        }

        if (order.getStatus() != STATUS_PENDING && order.getStatus() != STATUS_COOKING) {
            throw new BusinessException("订单状态不允许退款");
        }

        order.setStatus(STATUS_REFUNDING);
        String currentRemark = order.getRemark() != null ? order.getRemark() : "";
        order.setRemark(currentRemark + " | 退款原因: " + reason);
        orderMapper.updateById(order);

        log.info("用户 {} 申请退款订单 {}", userId, orderId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void confirmRefund(Long userId, Long orderId) {
        Order order = getOrderById(orderId);

        if (!order.getSellerId().equals(userId)) {
            throw new BusinessException("只有卖家可以确认退款");
        }

        if (order.getStatus() != STATUS_REFUNDING) {
            throw new BusinessException("订单状态不正确");
        }

        order.setStatus(STATUS_REFUNDED);
        orderMapper.updateById(order);

        log.info("用户 {} 确认退款订单 {}", userId, orderId);
    }

    @Override
    public OrderDTO getOrderDetail(Long userId, Long orderId) {
        Order order = getOrderById(orderId);

        // 验证权限
        Couple couple = getCoupleByUserId(userId);
        if (!order.getCoupleId().equals(couple.getId())) {
            throw new BusinessException("无权查看该订单");
        }

        return convertToOrderDTO(order);
    }

    @Override
    public Page<OrderDTO> getMyBuyOrders(Long userId, Integer status, Integer pageNum, Integer pageSize) {
        Page<Order> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<Order> wrapper = new LambdaQueryWrapper<Order>()
                .eq(Order::getBuyerId, userId)
                .orderByDesc(Order::getCreateTime);

        if (status != null) {
            wrapper.eq(Order::getStatus, status);
        }

        Page<Order> result = orderMapper.selectPage(page, wrapper);
        return convertToOrderDTOPage(result);
    }

    @Override
    public Page<OrderDTO> getMySellOrders(Long userId, Integer status, Integer pageNum, Integer pageSize) {
        Page<Order> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<Order> wrapper = new LambdaQueryWrapper<Order>()
                .eq(Order::getSellerId, userId)
                .orderByDesc(Order::getCreateTime);

        if (status != null) {
            wrapper.eq(Order::getStatus, status);
        }

        Page<Order> result = orderMapper.selectPage(page, wrapper);
        return convertToOrderDTOPage(result);
    }

    @Override
    public Page<OrderDTO> getCoupleOrders(Long userId, Integer status, Integer pageNum, Integer pageSize) {
        Couple couple = getCoupleByUserId(userId);

        Page<Order> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<Order> wrapper = new LambdaQueryWrapper<Order>()
                .eq(Order::getCoupleId, couple.getId())
                .orderByDesc(Order::getCreateTime);

        if (status != null) {
            wrapper.eq(Order::getStatus, status);
        }

        Page<Order> result = orderMapper.selectPage(page, wrapper);
        return convertToOrderDTOPage(result);
    }

    @Override
    public Integer getPendingOrderCount(Long userId) {
        // 作为买家的待处理订单
        Long buyCount = orderMapper.selectCount(
                new LambdaQueryWrapper<Order>()
                        .eq(Order::getBuyerId, userId)
                        .eq(Order::getStatus, STATUS_WAITING_DELIVERY)
        );

        // 作为卖家的待处理订单
        Long sellCount = orderMapper.selectCount(
                new LambdaQueryWrapper<Order>()
                        .eq(Order::getSellerId, userId)
                        .in(Order::getStatus, Arrays.asList(STATUS_PENDING, STATUS_COOKING))
        );

        return (buyCount != null ? buyCount.intValue() : 0) + (sellCount != null ? sellCount.intValue() : 0);
    }

    /**
     * 根据ID获取订单
     */
    private Order getOrderById(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new BusinessException("订单不存在");
        }
        return order;
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
     * 转换为DTO
     */
    private OrderDTO convertToOrderDTO(Order order) {
        OrderDTO dto = new OrderDTO();
        BeanUtils.copyProperties(order, dto);
        dto.setStatusDesc(getStatusDesc(order.getStatus()));

        // 获取用户信息
        Map<Long, User> userMap = getUserMap(new HashSet<>(Arrays.asList(order.getBuyerId(), order.getSellerId())));
        User buyer = userMap.get(order.getBuyerId());
        User seller = userMap.get(order.getSellerId());

        if (buyer != null) {
            dto.setBuyerName(buyer.getNickName());
            dto.setBuyerAvatar(buyer.getAvatarUrl());
        }
        if (seller != null) {
            dto.setSellerName(seller.getNickName());
            dto.setSellerAvatar(seller.getAvatarUrl());
        }

        // 获取菜谱封面
        Recipe recipe = recipeMapper.selectById(order.getRecipeId());
        if (recipe != null) {
            dto.setRecipeCoverUrl(recipe.getCoverUrl());
        }

        return dto;
    }

    /**
     * 转换分页
     */
    private Page<OrderDTO> convertToOrderDTOPage(Page<Order> page) {
        Page<OrderDTO> dtoPage = new Page<>();
        BeanUtils.copyProperties(page, dtoPage, "records");

        if (page.getRecords().isEmpty()) {
            dtoPage.setRecords(new ArrayList<>());
            return dtoPage;
        }

        // 批量获取用户信息
        Set<Long> userIds = new HashSet<>();
        page.getRecords().forEach(order -> {
            userIds.add(order.getBuyerId());
            userIds.add(order.getSellerId());
        });
        Map<Long, User> userMap = getUserMap(userIds);

        // 批量获取菜谱封面
        Set<Long> recipeIds = page.getRecords().stream()
                .map(Order::getRecipeId)
                .collect(Collectors.toSet());
        Map<Long, Recipe> recipeMap = getRecipeMap(recipeIds);

        List<OrderDTO> records = page.getRecords().stream()
                .map(order -> {
                    OrderDTO dto = new OrderDTO();
                    BeanUtils.copyProperties(order, dto);
                    dto.setStatusDesc(getStatusDesc(order.getStatus()));

                    User buyer = userMap.get(order.getBuyerId());
                    User seller = userMap.get(order.getSellerId());

                    if (buyer != null) {
                        dto.setBuyerName(buyer.getNickName());
                        dto.setBuyerAvatar(buyer.getAvatarUrl());
                    }
                    if (seller != null) {
                        dto.setSellerName(seller.getNickName());
                        dto.setSellerAvatar(seller.getAvatarUrl());
                    }

                    Recipe recipe = recipeMap.get(order.getRecipeId());
                    if (recipe != null) {
                        dto.setRecipeCoverUrl(recipe.getCoverUrl());
                    }

                    return dto;
                })
                .collect(Collectors.toList());

        dtoPage.setRecords(records);
        return dtoPage;
    }

    /**
     * 获取状态描述
     */
    private String getStatusDesc(Integer status) {
        switch (status) {
            case 0:
                return "待接单";
            case 1:
                return "制作中";
            case 2:
                return "待送达";
            case 3:
                return "已完成";
            case 4:
                return "已取消";
            case 5:
                return "退款中";
            case 6:
                return "已退款";
            default:
                return "未知";
        }
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
