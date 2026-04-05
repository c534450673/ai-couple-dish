package com.aicoupledish;

import com.aicoupledish.dao.mapper.NotificationMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Notification;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.service.impl.NotificationServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 通知服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("通知服务测试")
class NotificationServiceTest {

    @Mock
    private NotificationMapper notificationMapper;

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private NotificationServiceImpl notificationService;

    private User testUser;
    private Notification testNotification;

    @BeforeEach
    void setUp() {
        // 初始化测试用户
        testUser = new User();
        testUser.setId(1L);
        testUser.setOpenid("test_openid_001");
        testUser.setNickName("测试用户");
        testUser.setCoupleId(1L);

        // 初始化测试通知
        testNotification = new Notification();
        testNotification.setId(1L);
        testNotification.setUserId(1L);
        testNotification.setType(1);
        testNotification.setTitle("测试通知");
        testNotification.setContent("这是测试内容");
        testNotification.setIsRead(0);
        testNotification.setCreateTime(LocalDateTime.now());
    }

    @Nested
    @DisplayName("获取通知列表测试")
    class GetNotificationListTests {

        @Test
        @DisplayName("获取通知列表-成功")
        void getNotificationList_Success() {
            // Given
            when(notificationMapper.selectList(any())).thenReturn(Arrays.asList(testNotification));

            // When
            List<Notification> result = notificationService.getNotificationList(1L, null, null, null);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
        }

        @Test
        @DisplayName("获取通知列表-按类型筛选")
        void getNotificationList_FilterByType() {
            // Given
            when(notificationMapper.selectList(any())).thenReturn(Arrays.asList(testNotification));

            // When
            List<Notification> result = notificationService.getNotificationList(1L, 1, null, null);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
        }

        @Test
        @DisplayName("获取通知列表-空列表")
        void getNotificationList_EmptyList() {
            // Given
            when(notificationMapper.selectList(any())).thenReturn(Collections.emptyList());

            // When
            List<Notification> result = notificationService.getNotificationList(1L, null, null, null);

            // Then
            assertNotNull(result);
            assertTrue(result.isEmpty());
        }
    }

    @Nested
    @DisplayName("获取未读数量测试")
    class GetUnreadCountTests {

        @Test
        @DisplayName("获取未读数量-成功")
        void getUnreadCount_Success() {
            // Given
            when(notificationMapper.selectCount(any())).thenReturn(5L);

            // When
            Integer result = notificationService.getUnreadCount(1L);

            // Then
            assertEquals(5, result);
        }

        @Test
        @DisplayName("获取未读数量-无未读")
        void getUnreadCount_Zero() {
            // Given
            when(notificationMapper.selectCount(any())).thenReturn(0L);

            // When
            Integer result = notificationService.getUnreadCount(1L);

            // Then
            assertEquals(0, result);
        }
    }

    @Nested
    @DisplayName("标记已读测试")
    class MarkAsReadTests {

        @Test
        @DisplayName("标记已读-成功")
        void markAsRead_Success() {
            // Given
            when(notificationMapper.selectById(1L)).thenReturn(testNotification);
            when(notificationMapper.updateById(any(Notification.class))).thenReturn(1);

            // When
            notificationService.markAsRead(1L, 1L);

            // Then
            verify(notificationMapper).updateById(argThat(n ->
                n.getIsRead() == 1 && n.getReadTime() != null));
        }

        @Test
        @DisplayName("标记已读-通知不存在")
        void markAsRead_NotificationNotFound() {
            // Given
            when(notificationMapper.selectById(999L)).thenReturn(null);

            // When - should not throw
            assertDoesNotThrow(() -> notificationService.markAsRead(1L, 999L));

            // Then
            verify(notificationMapper, never()).updateById(any());
        }

        @Test
        @DisplayName("标记已读-用户不匹配")
        void markAsRead_UserMismatch() {
            // Given
            testNotification.setUserId(2L); // Different user
            when(notificationMapper.selectById(1L)).thenReturn(testNotification);

            // When - should not throw
            assertDoesNotThrow(() -> notificationService.markAsRead(1L, 1L));

            // Then
            verify(notificationMapper, never()).updateById(any());
        }
    }

    @Nested
    @DisplayName("全部标记已读测试")
    class MarkAllAsReadTests {

        @Test
        @DisplayName("全部标记已读-成功")
        void markAllAsRead_Success() {
            // Given
            when(notificationMapper.update(any(Notification.class), any())).thenReturn(5);

            // When
            notificationService.markAllAsRead(1L);

            // Then
            verify(notificationMapper).update(any(Notification.class), any());
        }
    }

    @Nested
    @DisplayName("删除通知测试")
    class DeleteNotificationTests {

        @Test
        @DisplayName("删除通知-成功")
        void deleteNotification_Success() {
            // Given
            when(notificationMapper.selectById(1L)).thenReturn(testNotification);
            when(notificationMapper.deleteById(1L)).thenReturn(1);

            // When
            notificationService.deleteNotification(1L, 1L);

            // Then
            verify(notificationMapper).deleteById(1L);
        }

        @Test
        @DisplayName("删除通知-通知不存在")
        void deleteNotification_NotFound() {
            // Given
            when(notificationMapper.selectById(999L)).thenReturn(null);

            // When - should not throw
            assertDoesNotThrow(() -> notificationService.deleteNotification(1L, 999L));

            // Then
            verify(notificationMapper, never()).deleteById(any());
        }

        @Test
        @DisplayName("删除通知-用户不匹配")
        void deleteNotification_UserMismatch() {
            // Given
            testNotification.setUserId(2L);
            when(notificationMapper.selectById(1L)).thenReturn(testNotification);

            // When - should not throw
            assertDoesNotThrow(() -> notificationService.deleteNotification(1L, 1L));

            // Then
            verify(notificationMapper, never()).deleteById(any());
        }
    }

    @Nested
    @DisplayName("发送通知测试")
    class SendNotificationTests {

        @Test
        @DisplayName("发送通知-成功")
        void sendNotification_Success() {
            // Given
            when(notificationMapper.insert(any(Notification.class))).thenReturn(1);

            // When
            notificationService.sendNotification(1L, 1, "测试标题", "测试内容", 1L, "test");

            // Then
            verify(notificationMapper).insert(argThat(n ->
                n.getUserId() == 1L &&
                n.getType() == 1 &&
                n.getTitle().equals("测试标题") &&
                n.getContent().equals("测试内容") &&
                n.getIsRead() == 0
            ));
        }
    }

    @Nested
    @DisplayName("发送情侣通知测试")
    class SendCoupleNotificationTests {

        @Test
        @DisplayName("发送情侣通知-成功")
        void sendCoupleNotification_Success() {
            // Given
            User partner = new User();
            partner.setId(2L);
            partner.setCoupleId(1L);

            when(userMapper.selectList(any())).thenReturn(Arrays.asList(testUser, partner));
            when(notificationMapper.insert(any(Notification.class))).thenReturn(1);

            // When
            notificationService.sendCoupleNotification(1L, 1L, 1, "标题", "内容", 1L, "type");

            // Then
            // Should only insert once (for partner, not for sender)
            verify(notificationMapper, times(1)).insert(any(Notification.class));
        }

        @Test
        @DisplayName("发送情侣通知-只有一方")
        void sendCoupleNotification_OnlyOneUser() {
            // Given
            when(userMapper.selectList(any())).thenReturn(Arrays.asList(testUser));
            when(notificationMapper.insert(any(Notification.class))).thenReturn(1);

            // When
            notificationService.sendCoupleNotification(1L, 1L, 1, "标题", "内容", 1L, "type");

            // Then
            // Should not insert since only one user and it's the sender
            verify(notificationMapper, never()).insert(any(Notification.class));
        }
    }
}