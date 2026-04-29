package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.AnniversaryMapper;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.FeedMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.CoupleHomeDTO;
import com.aicoupledish.domain.dto.CoupleInfoDTO;
import com.aicoupledish.domain.req.BindCoupleReq;
import com.aicoupledish.domain.req.GenerateCodeReq;
import com.aicoupledish.domain.req.UnbindReq;
import com.aicoupledish.service.impl.CoupleServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.RedisTemplate;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 情侣服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("情侣服务测试")
class CoupleServiceTest {

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private AnniversaryMapper anniversaryMapper;

    @Mock
    private FeedMapper feedMapper;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private HashOperations<String, Object, Object> hashOperations;

    @Mock
    private org.springframework.data.redis.core.ValueOperations<String, String> valueOperations;

    @InjectMocks
    private CoupleServiceImpl coupleService;

    private User testUser;
    private User partnerUser;
    private Couple testCouple;

    @BeforeEach
    void setUp() {
        // 初始化测试用户1
        testUser = new User();
        testUser.setId(1L);
        testUser.setOpenid("test_openid_001");
        testUser.setNickName("用户1");
        testUser.setAvatarUrl("https://example.com/avatar1.jpg");
        testUser.setStatus(0);
        testUser.setCreateTime(LocalDateTime.now());

        // 初始化测试用户2
        partnerUser = new User();
        partnerUser.setId(2L);
        partnerUser.setOpenid("test_openid_002");
        partnerUser.setNickName("用户2");
        partnerUser.setAvatarUrl("https://example.com/avatar2.jpg");
        partnerUser.setStatus(0);
        partnerUser.setCreateTime(LocalDateTime.now());

        // 初始化情侣关系
        testCouple = new Couple();
        testCouple.setId(1L);
        testCouple.setCoupleCode("ABC12345");
        testCouple.setUser1Id(1L);
        testCouple.setUser2Id(2L);
        testCouple.setStartDate(LocalDate.now().minusDays(100));
        testCouple.setLoveDays(100);
        testCouple.setStatus(1);
        testCouple.setCoupleNickname("用户1&用户2");
    }

    @Nested
    @DisplayName("生成情侣码测试")
    class GenerateCoupleCodeTests {

        @Test
        @DisplayName("生成情侣码-成功")
        void generateCoupleCode_Success() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(redisTemplate.opsForValue()).thenReturn(valueOperations);
            when(valueOperations.get(anyString())).thenReturn(null); // 没有现有情侣码
            when(redisTemplate.opsForHash()).thenReturn(hashOperations);
            when(redisTemplate.expire(anyString(), anyLong(), any(TimeUnit.class))).thenReturn(true);

            GenerateCodeReq req = new GenerateCodeReq();
            req.setLoveStartDate("2024-01-01");

            // When
            String coupleCode = coupleService.generateCoupleCode(1L, req);

            // Then
            assertNotNull(coupleCode);
            assertEquals(8, coupleCode.length());
            verify(hashOperations).put(anyString(), eq("userId"), eq("1"));
            verify(hashOperations).put(anyString(), eq("loveStartDate"), eq("2024-01-01"));
            verify(hashOperations).put(anyString(), eq("status"), eq("0"));
        }

        @Test
        @DisplayName("生成情侣码-用户已绑定应抛异常")
        void generateCoupleCode_AlreadyBound_ThrowsException() {
            // Given
            testUser.setCoupleId(1L);
            when(userMapper.selectById(1L)).thenReturn(testUser);

            GenerateCodeReq req = new GenerateCodeReq();
            req.setLoveStartDate("2024-01-01");

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> coupleService.generateCoupleCode(1L, req));
            assertEquals(BusinessException.COUPLE_ALREADY_BIND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("生成情侣码-用户不存在应抛异常")
        void generateCoupleCode_UserNotFound_ThrowsException() {
            // Given
            when(userMapper.selectById(999L)).thenReturn(null);

            GenerateCodeReq req = new GenerateCodeReq();
            req.setLoveStartDate("2024-01-01");

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> coupleService.generateCoupleCode(999L, req));
            assertEquals(BusinessException.USER_NOT_FOUND.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("绑定情侣测试")
    class BindCoupleTests {

        @Test
        @DisplayName("绑定情侣-成功")
        void bindCouple_Success() {
            // Given
            when(userMapper.selectById(2L)).thenReturn(testUser);
            when(userMapper.selectById(1L)).thenReturn(partnerUser);
            when(redisTemplate.opsForValue()).thenReturn(valueOperations);
            when(valueOperations.setIfAbsent(anyString(), anyString(), anyLong(), any(TimeUnit.class))).thenReturn(true);
            when(redisTemplate.hasKey("couple:code:ABC12345")).thenReturn(true);
            when(redisTemplate.opsForHash()).thenReturn(hashOperations);
            when(hashOperations.get("couple:code:ABC12345", "userId")).thenReturn("1");
            when(hashOperations.get("couple:code:ABC12345", "loveStartDate")).thenReturn("2024-01-01");
            when(redisTemplate.delete(anyString())).thenReturn(true);
            when(coupleMapper.insert(any(Couple.class))).thenReturn(1);
            when(userMapper.updateById(any(User.class))).thenReturn(1);

            BindCoupleReq req = new BindCoupleReq();
            req.setCoupleCode("ABC12345");

            // When
            CoupleInfoDTO result = coupleService.bindCouple(2L, req);

            // Then
            assertNotNull(result);
            assertEquals("ABC12345", result.getCoupleCode());
            assertEquals(1, result.getStatus());
            verify(coupleMapper).insert(any(Couple.class));
            verify(redisTemplate).delete("couple:code:ABC12345");
        }

        @Test
        @DisplayName("绑定情侣-用户已绑定应抛异常")
        void bindCouple_AlreadyBound_ThrowsException() {
            // Given
            testUser.setCoupleId(1L);
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(redisTemplate.opsForValue()).thenReturn(valueOperations);
            when(valueOperations.setIfAbsent(anyString(), anyString(), anyLong(), any(TimeUnit.class))).thenReturn(true);

            BindCoupleReq req = new BindCoupleReq();
            req.setCoupleCode("ABC12345");

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> coupleService.bindCouple(1L, req));
            assertEquals(BusinessException.COUPLE_ALREADY_BIND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("绑定情侣-情侣码无效应抛异常")
        void bindCouple_InvalidCode_ThrowsException() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(redisTemplate.opsForValue()).thenReturn(valueOperations);
            when(valueOperations.setIfAbsent(anyString(), anyString(), anyLong(), any(TimeUnit.class))).thenReturn(true);
            when(redisTemplate.hasKey("couple:code:INVALID")).thenReturn(false);

            BindCoupleReq req = new BindCoupleReq();
            req.setCoupleCode("INVALID");

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> coupleService.bindCouple(1L, req));
            assertEquals(BusinessException.COUPLE_CODE_INVALID.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("绑定情侣-自己绑定自己应抛异常")
        void bindCouple_SelfBind_ThrowsException() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(redisTemplate.opsForValue()).thenReturn(valueOperations);
            when(valueOperations.setIfAbsent(anyString(), anyString(), anyLong(), any(TimeUnit.class))).thenReturn(true);
            when(redisTemplate.hasKey("couple:code:ABC12345")).thenReturn(true);
            when(redisTemplate.opsForHash()).thenReturn(hashOperations);
            when(hashOperations.get("couple:code:ABC12345", "userId")).thenReturn("1");

            BindCoupleReq req = new BindCoupleReq();
            req.setCoupleCode("ABC12345");

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> coupleService.bindCouple(1L, req));
            assertEquals(BusinessException.COUPLE_BIND_CONFLICT.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("获取情侣信息测试")
    class GetCoupleInfoTests {

        @Test
        @DisplayName("获取情侣信息-成功")
        void getCoupleInfo_Success() {
            // Given
            testUser.setCoupleId(1L);
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(coupleMapper.selectById(1L)).thenReturn(testCouple);
            when(userMapper.selectById(2L)).thenReturn(partnerUser);

            // When
            CoupleInfoDTO result = coupleService.getCoupleInfo(1L);

            // Then
            assertNotNull(result);
            assertEquals(1L, result.getId());
            assertEquals("ABC12345", result.getCoupleCode());
            assertEquals(100, result.getLoveDays());
        }

        @Test
        @DisplayName("获取情侣信息-用户未绑定返回null")
        void getCoupleInfo_NotBound_ReturnsNull() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);

            // When
            CoupleInfoDTO result = coupleService.getCoupleInfo(1L);

            // Then
            assertNull(result);
        }

        @Test
        @DisplayName("获取情侣信息-情侣关系不存在返回null")
        void getCoupleInfo_CoupleNotExists_ReturnsNull() {
            // Given
            testUser.setCoupleId(999L);
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(coupleMapper.selectById(999L)).thenReturn(null);

            // When
            CoupleInfoDTO result = coupleService.getCoupleInfo(1L);

            // Then
            assertNull(result);
        }
    }

    @Nested
    @DisplayName("验证情侣码测试")
    class ValidateCoupleCodeTests {

        @Test
        @DisplayName("验证情侣码-有效")
        void validateCoupleCode_ValidCode_ReturnsTrue() {
            // Given
            when(redisTemplate.hasKey("couple:code:ABC12345")).thenReturn(true);

            // When
            boolean result = coupleService.validateCoupleCode("ABC12345");

            // Then
            assertTrue(result);
        }

        @Test
        @DisplayName("验证情侣码-无效")
        void validateCoupleCode_InvalidCode_ReturnsFalse() {
            // Given
            when(redisTemplate.hasKey("couple:code:INVALID")).thenReturn(false);

            // When
            boolean result = coupleService.validateCoupleCode("INVALID");

            // Then
            assertFalse(result);
        }
    }

    @Nested
    @DisplayName("申请解绑测试")
    class ApplyUnbindTests {

        @Test
        @DisplayName("申请解绑-成功")
        void applyUnbind_Success() {
            // Given
            testUser.setCoupleId(1L);
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(coupleMapper.selectById(1L)).thenReturn(testCouple);
            when(coupleMapper.updateById(any(Couple.class))).thenReturn(1);

            UnbindReq req = new UnbindReq();
            req.setOption("keep");

            // When
            assertDoesNotThrow(() -> coupleService.applyUnbind(1L, req));

            // Then
            verify(coupleMapper).updateById(argThat(c -> c.getStatus() == 3));
        }

        @Test
        @DisplayName("申请解绑-未绑定应抛异常")
        void applyUnbind_NotBound_ThrowsException() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);

            UnbindReq req = new UnbindReq();

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> coupleService.applyUnbind(1L, req));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("确认解绑测试")
    class ConfirmUnbindTests {

        @Test
        @DisplayName("确认解绑-成功")
        void confirmUnbind_Success() {
            // Given
            when(coupleMapper.selectById(1L)).thenReturn(testCouple);
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(userMapper.selectById(2L)).thenReturn(partnerUser);
            when(coupleMapper.updateById(any(Couple.class))).thenReturn(1);
            when(userMapper.updateById(any(User.class))).thenReturn(1);

            // When
            assertDoesNotThrow(() -> coupleService.confirmUnbind(1L, 1L));

            // Then
            verify(coupleMapper).updateById(argThat(c -> c.getStatus() == 2));
            verify(userMapper, times(2)).updateById(any(User.class));
        }

        @Test
        @DisplayName("确认解绑-情侣关系不存在应抛异常")
        void confirmUnbind_NotFound_ThrowsException() {
            // Given
            when(coupleMapper.selectById(999L)).thenReturn(null);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> coupleService.confirmUnbind(1L, 999L));
            assertEquals(BusinessException.COUPLE_NOT_FOUND.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("拒绝解绑测试")
    class RejectUnbindTests {

        @Test
        @DisplayName("拒绝解绑-成功")
        void rejectUnbind_Success() {
            // Given
            testCouple.setStatus(3);
            testCouple.setUnbindApplicantId(1L);
            when(coupleMapper.selectById(1L)).thenReturn(testCouple);
            when(coupleMapper.updateById(any(Couple.class))).thenReturn(1);

            // When
            assertDoesNotThrow(() -> coupleService.rejectUnbind(2L, 1L));

            // Then
            verify(coupleMapper).updateById(argThat(c -> c.getStatus() == 1));
        }
    }

    @Nested
    @DisplayName("获取恋爱计时测试")
    class GetLoveTimerTests {

        @Test
        @DisplayName("获取恋爱计时-成功")
        void getLoveTimer_Success() {
            // Given
            testUser.setCoupleId(1L);
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(coupleMapper.selectById(1L)).thenReturn(testCouple);
            when(anniversaryMapper.selectList(any())).thenReturn(new java.util.ArrayList<>());

            // When
            CoupleHomeDTO result = coupleService.getLoveTimer(1L);

            // Then
            assertNotNull(result);
            assertEquals(100, result.getLoveDays());
        }

        @Test
        @DisplayName("获取恋爱计时-未绑定返回空DTO")
        void getLoveTimer_NotBound_ReturnsEmptyDTO() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);

            // When
            CoupleHomeDTO result = coupleService.getLoveTimer(1L);

            // Then
            assertNotNull(result);
            assertNull(result.getLoveDays());
        }
    }
}