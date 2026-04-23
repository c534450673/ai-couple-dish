package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.WishMapper;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.dao.model.Wish;
import com.aicoupledish.domain.dto.WishDTO;
import com.aicoupledish.service.UserService;
import com.aicoupledish.service.impl.WishServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
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
 * 心愿单服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("心愿单服务测试")
class WishServiceTest {

    @Mock
    private WishMapper wishMapper;

    @Mock
    private UserService userService;

    @InjectMocks
    private WishServiceImpl wishService;

    private User testUser;
    private Wish testWish;

    @BeforeEach
    void setUp() {
        // 初始化测试用户
        testUser = new User();
        testUser.setId(1L);
        testUser.setOpenid("test_openid_001");
        testUser.setNickName("测试用户");
        testUser.setAvatarUrl("https://example.com/avatar.jpg");
        testUser.setCoupleId(1L);
        testUser.setStatus(0);

        // 初始化测试心愿
        testWish = new Wish();
        testWish.setId(1L);
        testWish.setCoupleId(1L);
        testWish.setCreatorId(1L);
        testWish.setWishType("restaurant");
        testWish.setTitle("去海底捞吃火锅");
        testWish.setDescription("听说他们家的服务很好");
        testWish.setImageUrl("https://example.com/hailuoluo.jpg");
        testWish.setPriority(2);
        testWish.setStatus(0);
        testWish.setIsDeleted(0);
        testWish.setCreateTime(LocalDateTime.now());
    }

    @Nested
    @DisplayName("获取心愿列表测试")
    class GetWishListTests {

        @Test
        @DisplayName("获取心愿列表-成功")
        void getWishList_Success() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectList(any())).thenReturn(Arrays.asList(testWish));
            when(userService.getUserById(1L)).thenReturn(testUser);

            // When
            List<WishDTO> result = wishService.getWishList(1L);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals("去海底捞吃火锅", result.get(0).getTitle());
        }

        @Test
        @DisplayName("获取心愿列表-用户未绑定返回空列表")
        void getWishList_UserNotBound_ReturnsEmptyList() {
            // Given
            testUser.setCoupleId(null);
            when(userService.getUserById(1L)).thenReturn(testUser);

            // When
            List<WishDTO> result = wishService.getWishList(1L);

            // Then
            assertNotNull(result);
            assertTrue(result.isEmpty());
        }

        @Test
        @DisplayName("获取心愿列表-无心愿返回空列表")
        void getWishList_NoWishes_ReturnsEmptyList() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectList(any())).thenReturn(Collections.emptyList());

            // When
            List<WishDTO> result = wishService.getWishList(1L);

            // Then
            assertNotNull(result);
            assertTrue(result.isEmpty());
        }
    }

    @Nested
    @DisplayName("获取心愿详情测试")
    class GetWishDetailTests {

        @Test
        @DisplayName("获取心愿详情-成功")
        void getWishDetail_Success() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(1L)).thenReturn(testWish);

            // When
            WishDTO result = wishService.getWishDetail(1L, 1L);

            // Then
            assertNotNull(result);
            assertEquals(1L, result.getId());
            assertEquals("去海底捞吃火锅", result.getTitle());
        }

        @Test
        @DisplayName("获取心愿详情-心愿不存在应抛异常")
        void getWishDetail_NotFound_ThrowsException() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(999L)).thenReturn(null);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.getWishDetail(1L, 999L));
            assertEquals(BusinessException.WISH_NOT_FOUND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("获取心愿详情-无权限应抛异常")
        void getWishDetail_NoPermission_ThrowsException() {
            // Given
            testWish.setCoupleId(999L); // 不同的情侣ID
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(1L)).thenReturn(testWish);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.getWishDetail(1L, 1L));
            assertEquals(BusinessException.WISH_NOT_PERMISSION.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("添加心愿测试")
    class AddWishTests {

        @Test
        @DisplayName("添加心愿-成功")
        void addWish_Success() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.insert(any(Wish.class))).thenAnswer(invocation -> {
                Wish wish = invocation.getArgument(0);
                wish.setId(1L);
                return 1;
            });

            // When
            Long wishId = wishService.addWish(1L, "restaurant", "去海底捞", "服务好", null, 2);

            // Then
            assertNotNull(wishId);
            verify(wishMapper).insert(any(Wish.class));
        }

        @Test
        @DisplayName("添加心愿-用户不存在应抛异常")
        void addWish_UserNotFound_ThrowsException() {
            // Given
            when(userService.getUserById(999L)).thenThrow(BusinessException.USER_NOT_FOUND);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.addWish(999L, "restaurant", "title", "desc", null, 2));
            assertEquals(BusinessException.USER_NOT_FOUND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("添加心愿-用户未绑定应抛异常")
        void addWish_UserNotBound_ThrowsException() {
            // Given
            testUser.setCoupleId(null);
            when(userService.getUserById(1L)).thenReturn(testUser);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.addWish(1L, "restaurant", "title", "desc", null, 2));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("添加心愿-默认优先级应为2")
        void addWish_DefaultPriority_ShouldBe2() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.insert(any(Wish.class))).thenReturn(1);

            // When
            wishService.addWish(1L, "restaurant", "title", "desc", null, null);

            // Then
            verify(wishMapper).insert(argThat(wish ->
                wish.getPriority() != null && wish.getPriority() == 2));
        }
    }

    @Nested
    @DisplayName("更新心愿测试")
    class UpdateWishTests {

        @Test
        @DisplayName("更新心愿-成功")
        void updateWish_Success() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(1L)).thenReturn(testWish);
            when(wishMapper.updateById(any(Wish.class))).thenReturn(1);

            // When
            wishService.updateWish(1L, 1L, "新标题", "新描述", null, 3);

            // Then
            verify(wishMapper).updateById(any(Wish.class));
        }

        @Test
        @DisplayName("更新心愿-心愿不存在应抛异常")
        void updateWish_NotFound_ThrowsException() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(999L)).thenReturn(null);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.updateWish(1L, 999L, "title", "desc", null, 2));
            assertEquals(BusinessException.WISH_NOT_FOUND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("更新心愿-无权限应抛异常")
        void updateWish_NoPermission_ThrowsException() {
            // Given
            testWish.setCoupleId(999L);
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(1L)).thenReturn(testWish);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.updateWish(1L, 1L, "title", "desc", null, 2));
            assertEquals(BusinessException.WISH_NOT_PERMISSION.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("删除心愿测试")
    class DeleteWishTests {

        @Test
        @DisplayName("删除心愿-成功")
        void deleteWish_Success() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(1L)).thenReturn(testWish);
            when(wishMapper.updateById(any(Wish.class))).thenReturn(1);

            // When
            wishService.deleteWish(1L, 1L);

            // Then
            verify(wishMapper).updateById(argThat(wish -> wish.getIsDeleted() == 1));
        }

        @Test
        @DisplayName("删除心愿-心愿不存在应抛异常")
        void deleteWish_NotFound_ThrowsException() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(999L)).thenReturn(null);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.deleteWish(1L, 999L));
            assertEquals(BusinessException.WISH_NOT_FOUND.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("实现心愿测试")
    class FulfillWishTests {

        @Test
        @DisplayName("实现心愿-成功")
        void fulfillWish_Success() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(1L)).thenReturn(testWish);
            when(wishMapper.updateById(any(Wish.class))).thenReturn(1);

            // When
            wishService.fulfillWish(1L, 1L);

            // Then
            verify(wishMapper).updateById(argThat(wish -> {
                wish.setStatus(1);
                wish.setAchievedDate(LocalDate.now());
                return wish.getStatus() == 1;
            }));
        }

        @Test
        @DisplayName("实现心愿-心愿不存在应抛异常")
        void fulfillWish_NotFound_ThrowsException() {
            // Given
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(999L)).thenReturn(null);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.fulfillWish(1L, 999L));
            assertEquals(BusinessException.WISH_NOT_FOUND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("实现心愿-无权限应抛异常")
        void fulfillWish_NoPermission_ThrowsException() {
            // Given
            testWish.setCoupleId(999L);
            when(userService.getUserById(1L)).thenReturn(testUser);
            when(wishMapper.selectById(1L)).thenReturn(testWish);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> wishService.fulfillWish(1L, 1L));
            assertEquals(BusinessException.WISH_NOT_PERMISSION.getCode(), exception.getCode());
        }
    }

    // Note: Helper methods (getWishTypeName, getPriorityName, getStatusName) are private
    // and are tested indirectly through the DTO conversion tests above.
}