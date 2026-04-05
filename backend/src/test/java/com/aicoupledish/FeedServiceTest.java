package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.FeedMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Feed;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.FeedDTO;
import com.aicoupledish.domain.dto.TodayFeedDTO;
import com.aicoupledish.domain.req.SendFeedReq;
import com.aicoupledish.service.impl.FeedServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 投喂服务单元测试
 * 测试范围：投喂发送、领取、拒绝、状态流转
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("投喂服务测试")
class FeedServiceTest {

    @Mock
    private FeedMapper feedMapper;

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private FeedServiceImpl feedService;

    private User testUser;
    private User testPartner;
    private Feed testFeed;

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

        // 初始化测试投喂
        testFeed = new Feed();
        testFeed.setId(1L);
        testFeed.setCoupleId(1L);
        testFeed.setSenderId(1L);
        testFeed.setReceiverId(2L);
        testFeed.setFeedType("meal");
        testFeed.setContent("今天给你点了外卖，记得吃哦");
        testFeed.setMessage("爱你哟");
        testFeed.setStatus(0); // 待领取
        testFeed.setExpireTime(LocalDateTime.now().plusHours(24));
        testFeed.setCreateTime(LocalDateTime.now());
    }

    @Test
    @DisplayName("获取今日投喂状态-已发送投喂")
    void getTodayFeedStatus_AlreadySent_ShouldReturnSentTrue() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(feedMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L);
        when(feedMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

        // When
        TodayFeedDTO result = feedService.getTodayFeedStatus(1L);

        // Then
        assertNotNull(result);
        assertTrue(result.getSentToday());
        assertFalse(result.getReceivedToday());
    }

    @Test
    @DisplayName("获取今日投喂状态-已收到待领取投喂")
    void getTodayFeedStatus_ReceivedPending_ShouldReturnReceivedTrue() {
        // Given
        when(userMapper.selectById(2L)).thenReturn(testPartner);
        when(feedMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
        when(feedMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(testFeed);

        // When
        TodayFeedDTO result = feedService.getTodayFeedStatus(2L);

        // Then
        assertNotNull(result);
        assertFalse(result.getSentToday());
        assertTrue(result.getReceivedToday());
        assertNotNull(result.getPendingFeed());
    }

    @Test
    @DisplayName("发送投喂-未绑定情侣应抛异常")
    void sendFeed_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        SendFeedReq req = new SendFeedReq();
        req.setFeedType("meal");
        req.setContent("测试投喂");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.sendFeed(99L, req));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("发送投喂-今日已发送应抛异常")
    void sendFeed_AlreadySentToday_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(userMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Arrays.asList(testPartner));
        when(feedMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(1L); // 今日已发送

        SendFeedReq req = new SendFeedReq();
        req.setFeedType("meal");
        req.setContent("测试投喂");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.sendFeed(1L, req));
        assertEquals(BusinessException.FEED_ALREADY_SENT.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("发送投喂-正餐类型应成功")
    void sendFeed_MealType_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(userMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Arrays.asList(testPartner));
        when(feedMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
        when(feedMapper.insert(any(Feed.class))).thenReturn(1);

        SendFeedReq req = new SendFeedReq();
        req.setFeedType("meal");
        req.setContent("今天给你点了外卖，记得吃哦");
        req.setMessage("爱你哟");

        // When
        Long feedId = feedService.sendFeed(1L, req);

        // Then
        assertNotNull(feedId);
        verify(feedMapper).insert(any(Feed.class));
    }

    @Test
    @DisplayName("发送投喂-甜品类型应成功")
    void sendFeed_DessertType_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(userMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Arrays.asList(testPartner));
        when(feedMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
        when(feedMapper.insert(any(Feed.class))).thenReturn(1);

        SendFeedReq req = new SendFeedReq();
        req.setFeedType("dessert");
        req.setContent("下午茶甜品");

        // When
        Long feedId = feedService.sendFeed(1L, req);

        // Then
        assertNotNull(feedId);
        verify(feedMapper).insert(any(Feed.class));
    }

    @Test
    @DisplayName("发送投喂-小吃类型应成功")
    void sendFeed_SnackType_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(userMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Arrays.asList(testPartner));
        when(feedMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
        when(feedMapper.insert(any(Feed.class))).thenReturn(1);

        SendFeedReq req = new SendFeedReq();
        req.setFeedType("snack");
        req.setContent("零食大礼包");

        // When
        Long feedId = feedService.sendFeed(1L, req);

        // Then
        assertNotNull(feedId);
    }

    @Test
    @DisplayName("发送投喂-饮品类型应成功")
    void sendFeed_DrinkType_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(userMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Arrays.asList(testPartner));
        when(feedMapper.selectCount(any(LambdaQueryWrapper.class))).thenReturn(0L);
        when(feedMapper.insert(any(Feed.class))).thenReturn(1);

        SendFeedReq req = new SendFeedReq();
        req.setFeedType("drink");
        req.setContent("奶茶一杯");

        // When
        Long feedId = feedService.sendFeed(1L, req);

        // Then
        assertNotNull(feedId);
    }

    @Test
    @DisplayName("获取已接收投喂列表")
    void getReceivedFeeds_ShouldReturnList() {
        // Given
        Feed feed1 = new Feed();
        feed1.setId(1L);
        feed1.setCoupleId(1L);
        feed1.setSenderId(1L);
        feed1.setReceiverId(2L);
        feed1.setFeedType("meal");
        feed1.setStatus(1); // 已领取

        Feed feed2 = new Feed();
        feed2.setId(2L);
        feed2.setCoupleId(1L);
        feed2.setSenderId(1L);
        feed2.setReceiverId(2L);
        feed2.setFeedType("dessert");
        feed2.setStatus(0); // 待领取

        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(feed2, feed1));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getReceivedFeeds(2L);

        // Then
        assertNotNull(result);
        assertEquals(2, result.size());
    }

    @Test
    @DisplayName("获取已发送投喂列表")
    void getSentFeeds_ShouldReturnList() {
        // Given
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("meal", result.get(0).getFeedType());
    }

    @Test
    @DisplayName("接受投喂-投喂不存在应抛异常")
    void acceptFeed_NotFound_ShouldThrowException() {
        // Given
        when(feedMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.acceptFeed(2L, 999L));
        assertEquals(BusinessException.FEED_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("接受投喂-非接收者不能接受")
    void acceptFeed_NotReceiver_ShouldThrowException() {
        // Given
        when(feedMapper.selectById(1L)).thenReturn(testFeed);

        // When & Then - 用户1是发送者，用户3尝试接受
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.acceptFeed(3L, 1L));
        assertEquals(BusinessException.FEED_CANNOT_ACCEPT.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("接受投喂-已领取的投喂不能再次接受")
    void acceptFeed_AlreadyAccepted_ShouldThrowException() {
        // Given
        testFeed.setStatus(1); // 已领取
        when(feedMapper.selectById(1L)).thenReturn(testFeed);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.acceptFeed(2L, 1L));
        assertEquals(BusinessException.FEED_EXPIRED.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("接受投喂-已拒绝的投喂不能接受")
    void acceptFeed_AlreadyRejected_ShouldThrowException() {
        // Given
        testFeed.setStatus(2); // 已拒绝
        when(feedMapper.selectById(1L)).thenReturn(testFeed);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.acceptFeed(2L, 1L));
        assertEquals(BusinessException.FEED_EXPIRED.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("接受投喂-已过期的投喂不能接受")
    void acceptFeed_Expired_ShouldThrowException() {
        // Given
        testFeed.setExpireTime(LocalDateTime.now().minusHours(1)); // 已过期
        when(feedMapper.selectById(1L)).thenReturn(testFeed);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.acceptFeed(2L, 1L));
        assertEquals(BusinessException.FEED_EXPIRED.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("接受投喂-有效投喂应成功")
    void acceptFeed_ValidFeed_ShouldSuccess() {
        // Given
        testFeed.setStatus(0);
        testFeed.setExpireTime(LocalDateTime.now().plusHours(24));
        when(feedMapper.selectById(1L)).thenReturn(testFeed);
        when(feedMapper.updateById(any(Feed.class))).thenReturn(1);

        // When
        feedService.acceptFeed(2L, 1L);

        // Then
        verify(feedMapper).updateById(argThat(feed ->
            feed.getStatus() == 1 && feed.getReceiveTime() != null));
    }

    @Test
    @DisplayName("拒绝投喂-投喂不存在应抛异常")
    void rejectFeed_NotFound_ShouldThrowException() {
        // Given
        when(feedMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.rejectFeed(2L, 999L, "不想吃"));
        assertEquals(BusinessException.FEED_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("拒绝投喂-非接收者不能拒绝")
    void rejectFeed_NotReceiver_ShouldThrowException() {
        // Given
        when(feedMapper.selectById(1L)).thenReturn(testFeed);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> feedService.rejectFeed(3L, 1L, "理由"));
        assertEquals(BusinessException.FEED_CANNOT_ACCEPT.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("拒绝投喂-有效请求应成功")
    void rejectFeed_ValidRequest_ShouldSuccess() {
        // Given
        when(feedMapper.selectById(1L)).thenReturn(testFeed);
        when(feedMapper.updateById(any(Feed.class))).thenReturn(1);

        // When
        feedService.rejectFeed(2L, 1L, "今天胃口不好");

        // Then
        verify(feedMapper).updateById(argThat(feed ->
            feed.getStatus() == 2 && "今天胃口不好".equals(feed.getRejectReason())));
    }

    @Test
    @DisplayName("拒绝投喂-不填写理由应成功")
    void rejectFeed_NoReason_ShouldSuccess() {
        // Given
        when(feedMapper.selectById(1L)).thenReturn(testFeed);
        when(feedMapper.updateById(any(Feed.class))).thenReturn(1);

        // When
        feedService.rejectFeed(2L, 1L, null);

        // Then
        verify(feedMapper).updateById(argThat(feed ->
            feed.getStatus() == 2));
    }

    @Test
    @DisplayName("投喂类型名称转换-meal")
    void feedTypeName_Meal_ShouldReturn正餐() {
        // Given
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertEquals("正餐", result.get(0).getFeedTypeName());
    }

    @Test
    @DisplayName("投喂类型名称转换-dessert")
    void feedTypeName_Dessert_ShouldReturn甜品() {
        // Given
        testFeed.setFeedType("dessert");
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertEquals("甜品", result.get(0).getFeedTypeName());
    }

    @Test
    @DisplayName("投喂类型名称转换-snack")
    void feedTypeName_Snack_ShouldReturn小吃() {
        // Given
        testFeed.setFeedType("snack");
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertEquals("小吃", result.get(0).getFeedTypeName());
    }

    @Test
    @DisplayName("投喂类型名称转换-drink")
    void feedTypeName_Drink_ShouldReturn饮品() {
        // Given
        testFeed.setFeedType("drink");
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertEquals("饮品", result.get(0).getFeedTypeName());
    }

    @Test
    @DisplayName("投喂状态名称转换-待领取")
    void feedStatusName_Pending_ShouldReturn待领取() {
        // Given
        testFeed.setStatus(0);
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertEquals("待领取", result.get(0).getStatusName());
    }

    @Test
    @DisplayName("投喂状态名称转换-已领取")
    void feedStatusName_Accepted_ShouldReturn已领取() {
        // Given
        testFeed.setStatus(1);
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertEquals("已领取", result.get(0).getStatusName());
    }

    @Test
    @DisplayName("投喂状态名称转换-已拒绝")
    void feedStatusName_Rejected_ShouldReturn已拒绝() {
        // Given
        testFeed.setStatus(2);
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testFeed));
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        List<FeedDTO> result = feedService.getSentFeeds(1L);

        // Then
        assertEquals("已拒绝", result.get(0).getStatusName());
    }

    @Test
    @DisplayName("获取已接收投喂列表-空列表")
    void getReceivedFeeds_EmptyList_ShouldReturnEmptyList() {
        // Given
        when(feedMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Collections.emptyList());

        // When
        List<FeedDTO> result = feedService.getReceivedFeeds(2L);

        // Then
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }
}
