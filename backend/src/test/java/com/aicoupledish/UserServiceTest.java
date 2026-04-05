package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.LoginRespDTO;
import com.aicoupledish.domain.dto.UserInfoDTO;
import com.aicoupledish.domain.req.WechatLoginReq;
import com.aicoupledish.service.impl.UserServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.LocalDateTime;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 用户服务单元测试
 * 测试范围：用户登录、用户信息获取、用户信息更新
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("用户服务测试")
class UserServiceTest {

    @Mock
    private UserMapper userMapper;

    @Mock
    private JwtUtils jwtUtils;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    @InjectMocks
    private UserServiceImpl userService;

    private User testUser;
    private WechatLoginReq loginReq;

    @BeforeEach
    void setUp() {
        // 初始化测试用户
        testUser = new User();
        testUser.setId(1L);
        testUser.setOpenid("test_openid_001");
        testUser.setNickName("测试用户");
        testUser.setAvatarUrl("https://example.com/avatar.jpg");
        testUser.setStatus(0);
        testUser.setMemberLevel(0);
        testUser.setGender(1);
        testUser.setCreateTime(LocalDateTime.now());

        // 初始化登录请求
        loginReq = new WechatLoginReq();
        loginReq.setCode("test_openid_001");
        loginReq.setNickName("测试用户");
        loginReq.setAvatarUrl("https://example.com/avatar.jpg");
    }

    @Test
    @DisplayName("微信登录-新用户首次登录")
    void wechatLogin_NewUser_ShouldCreateUser() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(anyString())).thenReturn(null);
        when(userMapper.selectOne(any())).thenReturn(null);
        when(userMapper.insert(any(User.class))).thenReturn(1);
        when(jwtUtils.generateToken(anyLong())).thenReturn("test_token_12345");

        // When
        LoginRespDTO result = userService.wechatLogin(loginReq);

        // Then
        assertNotNull(result);
        assertEquals("test_token_12345", result.getToken());
        assertNotNull(result.getUserInfo());
        assertEquals("test_openid_001", result.getUserInfo().getOpenid());
        verify(userMapper).insert(any(User.class));
    }

    @Test
    @DisplayName("微信登录-老用户登录")
    void wechatLogin_ExistingUser_ShouldUpdateUser() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(anyString())).thenReturn(null);
        when(userMapper.selectOne(any())).thenReturn(testUser);
        when(userMapper.updateById(any(User.class))).thenReturn(1);
        when(jwtUtils.generateToken(anyLong())).thenReturn("test_token_12345");

        // When
        LoginRespDTO result = userService.wechatLogin(loginReq);

        // Then
        assertNotNull(result);
        assertEquals("test_token_12345", result.getToken());
        assertNotNull(result.getUserInfo());
        assertEquals("测试用户", result.getUserInfo().getNickName());
        verify(userMapper).updateById(any(User.class));
        verify(userMapper, never()).insert(any(User.class));
    }

    @Test
    @DisplayName("微信登录-无openid应抛异常")
    void wechatLogin_NoOpenid_ShouldThrowException() {
        // Given
        loginReq.setCode(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.wechatLogin(loginReq));
        assertEquals(BusinessException.USER_NOT_LOGGED_IN.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("微信登录-empty openid应抛异常")
    void wechatLogin_EmptyOpenid_ShouldThrowException() {
        // Given
        loginReq.setCode("");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.wechatLogin(loginReq));
        assertEquals(BusinessException.USER_NOT_LOGGED_IN.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取用户信息-用户存在")
    void getUserInfo_UserExists_ShouldReturnUserInfo() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:info:1")).thenReturn(null);
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        UserInfoDTO result = userService.getUserInfo(1L);

        // Then
        assertNotNull(result);
        assertEquals(1L, result.getId());
        assertEquals("测试用户", result.getNickName());
        assertEquals("test_openid_001", result.getOpenid());
    }

    @Test
    @DisplayName("获取用户信息-用户不存在应抛异常")
    void getUserInfo_UserNotFound_ShouldThrowException() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(anyString())).thenReturn(null);
        when(userMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.getUserInfo(999L));
        assertEquals(BusinessException.USER_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取用户信息-缓存命中")
    void getUserInfo_CacheHit_ShouldReturnFromCache() {
        // Given
        String cachedUserJson = "{\"id\":1,\"openid\":\"test_openid_001\",\"nickName\":\"缓存用户\"}";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:info:1")).thenReturn(cachedUserJson);

        // When
        UserInfoDTO result = userService.getUserInfo(1L);

        // Then
        assertNotNull(result);
        assertEquals(1L, result.getId());
        assertEquals("缓存用户", result.getNickName());
        verify(userMapper, never()).selectById(any());
    }

    @Test
    @DisplayName("更新用户信息-更新昵称")
    void updateUserInfo_UpdateNickname_ShouldSuccess() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:info:1")).thenReturn(null);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(userMapper.updateById(any(User.class))).thenReturn(1);
        when(redisTemplate.delete(anyString())).thenReturn(true);

        // When
        userService.updateUserInfo(1L, "新昵称", null);

        // Then
        verify(userMapper).updateById(argThat(user ->
            user.getNickName().equals("新昵称")));
        verify(redisTemplate).delete("user:info:1");
    }

    @Test
    @DisplayName("更新用户信息-更新头像")
    void updateUserInfo_UpdateAvatar_ShouldSuccess() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:info:1")).thenReturn(null);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(userMapper.updateById(any(User.class))).thenReturn(1);
        when(redisTemplate.delete(anyString())).thenReturn(true);

        // When
        userService.updateUserInfo(1L, null, "https://new-avatar.com/avatar.jpg");

        // Then
        verify(userMapper).updateById(argThat(user ->
            user.getAvatarUrl().equals("https://new-avatar.com/avatar.jpg")));
        verify(redisTemplate).delete("user:info:1");
    }

    @Test
    @DisplayName("根据openid获取用户ID-缓存未命中")
    void getUserIdByOpenid_CacheMiss_ShouldQueryDatabase() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:openid:test_openid_001")).thenReturn(null);
        when(userMapper.selectOne(any())).thenReturn(testUser);

        // When
        Long userId = userService.getUserIdByOpenid("test_openid_001");

        // Then
        assertEquals(1L, userId);
        // Verify database was queried
        verify(userMapper).selectOne(any());
    }

    @Test
    @DisplayName("根据openid获取用户ID-缓存命中")
    void getUserIdByOpenid_CacheHit_ShouldReturnFromCache() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:openid:test_openid_001")).thenReturn("1");

        // When
        Long userId = userService.getUserIdByOpenid("test_openid_001");

        // Then
        assertEquals(1L, userId);
        verify(userMapper, never()).selectOne(any());
    }

    @Test
    @DisplayName("根据openid获取用户ID-用户不存在返回null")
    void getUserIdByOpenid_UserNotFound_ShouldReturnNull() {
        // Given
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(anyString())).thenReturn(null);
        when(userMapper.selectOne(any())).thenReturn(null);

        // When
        Long userId = userService.getUserIdByOpenid("nonexistent_openid");

        // Then
        assertNull(userId);
    }
}
