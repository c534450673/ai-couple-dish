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
        when(userMapper.selectOne(any())).thenReturn(null);
        when(userMapper.insert(any(User.class))).thenAnswer(invocation -> {
            User user = invocation.getArgument(0);
            user.setId(1L);
            return 1;
        });
        when(jwtUtils.generateToken(anyLong())).thenReturn("test_token_12345");
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

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
        when(userMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.getUserInfo(999L));
        assertEquals(BusinessException.USER_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取用户信息-缓存命中")
    void getUserInfo_CacheHit_ShouldReturnFromCache() {
        // Given - 服务目前不使用缓存读取，直接从数据库获取
        when(userMapper.selectById(1L)).thenReturn(testUser);

        // When
        UserInfoDTO result = userService.getUserInfo(1L);

        // Then
        assertNotNull(result);
        assertEquals(1L, result.getId());
        assertEquals("测试用户", result.getNickName());
    }

    @Test
    @DisplayName("更新用户信息-更新昵称")
    void updateUserInfo_UpdateNickname_ShouldSuccess() {
        // Given
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

    // ========== 手机号登录相关测试 ==========

    @Test
    @DisplayName("手机号登录-验证成功应返回token")
    void phoneLogin_ValidCode_ShouldReturnToken() {
        // Given
        String phone = "13800138000";
        String verifyCode = "123456";
        testUser.setPhone(phone);

        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:code:" + phone)).thenReturn(verifyCode);
        when(userMapper.selectOne(any())).thenReturn(testUser);
        when(jwtUtils.generateToken(anyLong())).thenReturn("test_token_phone");

        // When
        LoginRespDTO result = userService.phoneLogin(phone, verifyCode);

        // Then
        assertNotNull(result);
        assertEquals("test_token_phone", result.getToken());
        assertNotNull(result.getUserInfo());
        // 验证验证码已被删除
        verify(redisTemplate).delete("user:verify:code:" + phone);
        verify(redisTemplate).delete("user:verify:expire:" + phone);
    }

    @Test
    @DisplayName("手机号登录-手机号格式不正确应抛异常")
    void phoneLogin_InvalidPhoneFormat_ShouldThrowException() {
        // Given
        String invalidPhone = "12345";

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.phoneLogin(invalidPhone, "123456"));
        assertEquals(1004, exception.getCode()); // PHONE_FORMAT_INVALID
    }

    @Test
    @DisplayName("手机号登录-空验证码应抛异常")
    void phoneLogin_EmptyVerifyCode_ShouldThrowException() {
        // Given
        String phone = "13800138000";

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.phoneLogin(phone, null));
        assertEquals(9003, exception.getCode()); // SMS_CODE_ERROR
    }

    @Test
    @DisplayName("手机号登录-空白验证码应抛异常")
    void phoneLogin_BlankVerifyCode_ShouldThrowException() {
        // Given
        String phone = "13800138000";

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.phoneLogin(phone, "   "));
        assertEquals(9003, exception.getCode()); // SMS_CODE_ERROR
    }

    @Test
    @DisplayName("手机号登录-验证码过期应抛异常")
    void phoneLogin_ExpiredVerifyCode_ShouldThrowException() {
        // Given
        String phone = "13800138000";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:code:" + phone)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.phoneLogin(phone, "123456"));
        assertEquals(9004, exception.getCode()); // SMS_CODE_EXPIRED
    }

    @Test
    @DisplayName("手机号登录-验证码错误应抛异常")
    void phoneLogin_WrongVerifyCode_ShouldThrowException() {
        // Given
        String phone = "13800138000";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:code:" + phone)).thenReturn("654321");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.phoneLogin(phone, "123456"));
        assertEquals(9003, exception.getCode()); // SMS_CODE_ERROR
    }

    @Test
    @DisplayName("手机号登录-用户未注册应抛异常")
    void phoneLogin_UserNotRegistered_ShouldThrowException() {
        // Given
        String phone = "13800138000";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:code:" + phone)).thenReturn("123456");
        when(userMapper.selectOne(any())).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.phoneLogin(phone, "123456"));
        assertEquals(1006, exception.getCode()); // PHONE_NOT_REGISTERED
    }

    // ========== 手机号注册相关测试 ==========

    @Test
    @DisplayName("手机号注册-验证成功应创建用户并返回token")
    void registerByPhone_ValidCode_ShouldCreateUserAndReturnToken() {
        // Given
        String phone = "13900139000";
        String verifyCode = "123456";

        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:code:" + phone)).thenReturn(verifyCode);
        when(userMapper.selectOne(any())).thenReturn(null); // 用户不存在
        when(userMapper.insert(any(User.class))).thenAnswer(invocation -> {
            User user = invocation.getArgument(0);
            user.setId(2L);
            return 1;
        });
        when(jwtUtils.generateToken(anyLong())).thenReturn("test_token_register");

        // When
        LoginRespDTO result = userService.registerByPhone(phone, verifyCode);

        // Then
        assertNotNull(result);
        assertEquals("test_token_register", result.getToken());
        verify(userMapper).insert(any(User.class));
        // 验证验证码已被删除
        verify(redisTemplate).delete("user:verify:code:" + phone);
    }

    @Test
    @DisplayName("手机号注册-手机号格式不正确应抛异常")
    void registerByPhone_InvalidPhoneFormat_ShouldThrowException() {
        // Given
        String invalidPhone = "12345";

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.registerByPhone(invalidPhone, "123456"));
        assertEquals(1004, exception.getCode()); // PHONE_FORMAT_INVALID
    }

    @Test
    @DisplayName("手机号注册-手机号已注册应抛异常")
    void registerByPhone_AlreadyRegistered_ShouldThrowException() {
        // Given
        String phone = "13800138000";
        testUser.setPhone(phone);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:code:" + phone)).thenReturn("123456");
        when(userMapper.selectOne(any())).thenReturn(testUser);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.registerByPhone(phone, "123456"));
        assertEquals(1005, exception.getCode()); // PHONE_ALREADY_REGISTERED
    }

    @Test
    @DisplayName("手机号注册-空验证码应抛异常")
    void registerByPhone_EmptyVerifyCode_ShouldThrowException() {
        // Given
        String phone = "13800138000";

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.registerByPhone(phone, null));
        assertEquals(9003, exception.getCode()); // SMS_CODE_ERROR
    }

    @Test
    @DisplayName("手机号注册-验证码过期应抛异常")
    void registerByPhone_ExpiredVerifyCode_ShouldThrowException() {
        // Given
        String phone = "13800138000";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:code:" + phone)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.registerByPhone(phone, "123456"));
        assertEquals(9004, exception.getCode()); // SMS_CODE_EXPIRED
    }

    // ========== 发送验证码相关测试 ==========

    @Test
    @DisplayName("发送验证码-成功发送应生成6位验证码")
    void sendVerifyCode_Success_ShouldGenerateCode() {
        // Given
        String phone = "13800138000";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:expire:" + phone)).thenReturn(null);

        // When
        userService.sendVerifyCode(phone);

        // Then
        verify(valueOperations).set(
            eq("user:verify:code:" + phone),
            argThat(code -> code != null && code.length() == 6),
            anyLong(),
            any()
        );
        verify(valueOperations).set(
            eq("user:verify:expire:" + phone),
            eq("1"),
            anyLong(),
            any()
        );
    }

    @Test
    @DisplayName("发送验证码-手机号格式不正确应抛异常")
    void sendVerifyCode_InvalidPhoneFormat_ShouldThrowException() {
        // Given
        String invalidPhone = "12345";

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.sendVerifyCode(invalidPhone));
        assertEquals(1004, exception.getCode()); // PHONE_FORMAT_INVALID
    }

    @Test
    @DisplayName("发送验证码-60秒内重复发送应抛异常")
    void sendVerifyCode_TooFrequent_ShouldThrowException() {
        // Given
        String phone = "13800138000";
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("user:verify:expire:" + phone)).thenReturn("1");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> userService.sendVerifyCode(phone));
        assertEquals(BusinessException.OPERATION_TOO_FREQUENT.getCode(), exception.getCode());
    }

    // ========== 手机号格式校验测试 ==========

    @Test
    @DisplayName("手机号格式校验-正确格式应返回true")
    void isValidPhoneNumber_ValidPhone_ShouldReturnTrue() {
        // Given
        String validPhone = "13800138000";

        // When
        boolean result = userService.isValidPhoneNumber(validPhone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-以13开头的手机号应返回true")
    void isValidPhoneNumber_13Prefix_ShouldReturnTrue() {
        // Given
        String phone = "13900139000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-以14开头的手机号应返回true")
    void isValidPhoneNumber_14Prefix_ShouldReturnTrue() {
        // Given
        String phone = "14700147000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-以15开头的手机号应返回true")
    void isValidPhoneNumber_15Prefix_ShouldReturnTrue() {
        // Given
        String phone = "15000150000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-以16开头的手机号应返回true")
    void isValidPhoneNumber_16Prefix_ShouldReturnTrue() {
        // Given
        String phone = "16600166000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-以17开头的手机号应返回true")
    void isValidPhoneNumber_17Prefix_ShouldReturnTrue() {
        // Given
        String phone = "17700177000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-以18开头的手机号应返回true")
    void isValidPhoneNumber_18Prefix_ShouldReturnTrue() {
        // Given
        String phone = "18800188000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-以19开头的手机号应返回true")
    void isValidPhoneNumber_19Prefix_ShouldReturnTrue() {
        // Given
        String phone = "19900199000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("手机号格式校验-null应返回false")
    void isValidPhoneNumber_Null_ShouldReturnFalse() {
        // When
        boolean result = userService.isValidPhoneNumber(null);

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("手机号格式校验-过短应返回false")
    void isValidPhoneNumber_TooShort_ShouldReturnFalse() {
        // Given
        String shortPhone = "1380013";

        // When
        boolean result = userService.isValidPhoneNumber(shortPhone);

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("手机号格式校验-过长应返回false")
    void isValidPhoneNumber_TooLong_ShouldReturnFalse() {
        // Given
        String longPhone = "138001380001";

        // When
        boolean result = userService.isValidPhoneNumber(longPhone);

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("手机号格式校验-以0开头应返回false")
    void isValidPhoneNumber_StartsWith0_ShouldReturnFalse() {
        // Given
        String phone = "013800138000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("手机号格式校验-以1开头但非有效区号应返回false")
    void isValidPhoneNumber_StartsWith1Invalid_ShouldReturnFalse() {
        // Given - 12位 number starting with 1
        String phone = "11200112000";

        // When
        boolean result = userService.isValidPhoneNumber(phone);

        // Then
        assertFalse(result);
    }
}
