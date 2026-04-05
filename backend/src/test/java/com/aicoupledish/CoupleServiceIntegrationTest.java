package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.req.BindCoupleReq;
import com.aicoupledish.domain.req.GenerateCodeReq;
import com.aicoupledish.service.impl.CoupleServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.RedisTemplate;

import java.time.LocalDate;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 情侣服务集成测试
 * 测试范围：情侣绑定流程、情侣码生成、情侣信息获取、解绑流程
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("情侣服务集成测试")
class CoupleServiceIntegrationTest {

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private HashOperations<String, Object, Object> hashOperations;

    @InjectMocks
    private CoupleServiceImpl coupleService;

    private User user1;
    private User user2;
    private User unboundUser;
    private Couple testCouple;

    @BeforeEach
    void setUp() {
        // 初始化用户1 - 小明（未绑定）
        user1 = new User();
        user1.setId(1L);
        user1.setNickName("小明");
        user1.setAvatarUrl("https://example.com/avatar1.jpg");
        user1.setOpenid("openid_001");
        user1.setCoupleId(null);
        user1.setStatus(0);

        // 初始化用户2 - 小红（未绑定）
        user2 = new User();
        user2.setId(2L);
        user2.setNickName("小红");
        user2.setAvatarUrl("https://example.com/avatar2.jpg");
        user2.setOpenid("openid_002");
        user2.setCoupleId(null);
        user2.setStatus(0);

        // 初始化未绑定用户
        unboundUser = new User();
        unboundUser.setId(3L);
        unboundUser.setNickName("小华");
        unboundUser.setCoupleId(null);
        unboundUser.setStatus(0);

        // 初始化已绑定情侣
        testCouple = new Couple();
        testCouple.setId(1L);
        testCouple.setCoupleCode("TEST1234");
        testCouple.setUser1Id(1L);
        testCouple.setUser2Id(2L);
        testCouple.setStartDate(LocalDate.of(2025, 11, 11));
        testCouple.setLoveDays(130);
        testCouple.setCoupleNickname("小明&小红");
        testCouple.setStatus(1); // 已绑定
        testCouple.setCreateTime(LocalDateTime.now());
    }

    @Test
    @DisplayName("生成情侣码-未绑定用户应成功")
    void generateCoupleCode_UnboundUser_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(user1);
        when(redisTemplate.opsForHash()).thenReturn(hashOperations);

        GenerateCodeReq req = new GenerateCodeReq();
        req.setLoveStartDate("2026-03-21");

        // When
        String coupleCode = coupleService.generateCoupleCode(1L, req);

        // Then
        assertNotNull(coupleCode);
        assertEquals(8, coupleCode.length());
        verify(redisTemplate.opsForHash(), times(3)).put(anyString(), anyString(), anyString());
    }

    @Test
    @DisplayName("生成情侣码-已绑定用户应抛异常")
    void generateCoupleCode_AlreadyBound_ShouldThrowException() {
        // Given
        user1.setCoupleId(1L); // 已绑定
        when(userMapper.selectById(1L)).thenReturn(user1);

        GenerateCodeReq req = new GenerateCodeReq();

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> coupleService.generateCoupleCode(1L, req));
        assertEquals(BusinessException.COUPLE_ALREADY_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("绑定情侣-有效情侣码应成功")
    void bindCouple_ValidCode_ShouldSuccess() {
        // Given
        user1.setCoupleId(null);
        user2.setCoupleId(null);

        when(userMapper.selectById(1L)).thenReturn(user1);
        when(userMapper.selectById(2L)).thenReturn(user2);
        when(redisTemplate.hasKey(anyString())).thenReturn(true);
        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        when(hashOperations.get(anyString(), eq("userId"))).thenReturn("1");
        when(hashOperations.get(anyString(), eq("loveStartDate"))).thenReturn("2026-03-21");
        when(hashOperations.get(anyString(), eq("status"))).thenReturn("0");
        when(coupleMapper.insert(any(Couple.class))).thenReturn(1);
        when(coupleMapper.updateById(any(Couple.class))).thenReturn(1);
        when(userMapper.updateById(any(User.class))).thenReturn(1);
        when(redisTemplate.delete(anyString())).thenReturn(true);

        BindCoupleReq req = new BindCoupleReq();
        req.setCoupleCode("PENDING1");

        // When
        var result = coupleService.bindCouple(2L, req);

        // Then
        assertNotNull(result);
        verify(coupleMapper).insert(any(Couple.class));
        verify(userMapper, times(2)).updateById(any(User.class));
    }

    @Test
    @DisplayName("绑定情侣-无效情侣码应抛异常")
    void bindCouple_InvalidCode_ShouldThrowException() {
        // Given
        user2.setCoupleId(null);
        when(userMapper.selectById(2L)).thenReturn(user2);
        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        BindCoupleReq req = new BindCoupleReq();
        req.setCoupleCode("INVALID");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> coupleService.bindCouple(2L, req));
        assertEquals(BusinessException.COUPLE_CODE_INVALID.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取情侣信息-已绑定应返回信息")
    void getCoupleInfo_BoundCouple_ShouldReturnInfo() {
        // Given
        user1.setCoupleId(1L);
        user1.setLoveStartDate(LocalDateTime.of(2025, 11, 11, 0, 0, 0));

        when(userMapper.selectById(1L)).thenReturn(user1);
        when(userMapper.selectById(2L)).thenReturn(user2);
        when(coupleMapper.selectById(1L)).thenReturn(testCouple);

        // When
        var result = coupleService.getCoupleInfo(1L);

        // Then
        assertNotNull(result);
        assertNotNull(result.getUser1Id());
        assertNotNull(result.getUser2Id());
    }

    @Test
    @DisplayName("获取情侣信息-未绑定应返回null")
    void getCoupleInfo_NotBound_ShouldReturnNull() {
        // Given
        when(userMapper.selectById(3L)).thenReturn(unboundUser);

        // When
        var result = coupleService.getCoupleInfo(3L);

        // Then
        assertNull(result);
    }

    @Test
    @DisplayName("验证情侣码-有效码应返回true")
    void validateCoupleCode_ValidCode_ShouldReturnTrue() {
        // Given
        when(redisTemplate.hasKey(anyString())).thenReturn(true);

        // When
        boolean result = coupleService.validateCoupleCode("TEST1234");

        // Then
        assertTrue(result);
    }

    @Test
    @DisplayName("验证情侣码-无效码应返回false")
    void validateCoupleCode_InvalidCode_ShouldReturnFalse() {
        // Given
        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        // When
        boolean result = coupleService.validateCoupleCode("INVALID");

        // Then
        assertFalse(result);
    }

    @Test
    @DisplayName("恋爱天数计算-正确计算")
    void loveDaysCalculation_ShouldBeCorrect() {
        // Given
        user1.setCoupleId(1L);
        user1.setLoveStartDate(LocalDateTime.of(2025, 11, 11, 0, 0, 0));

        when(userMapper.selectById(1L)).thenReturn(user1);
        when(coupleMapper.selectById(1L)).thenReturn(testCouple);

        // When
        var result = coupleService.getLoveTimer(1L);

        // Then
        assertNotNull(result);
        assertTrue(result.getLoveDays() >= 130);
    }

    @Test
    @DisplayName("申请解绑-应更新状态为申请解绑中")
    void applyUnbind_ShouldUpdateStatusToApplying() {
        // Given
        user1.setCoupleId(1L);
        user1.setLoveStartDate(LocalDateTime.now().minusDays(100));

        Couple boundCouple = new Couple();
        boundCouple.setId(1L);
        boundCouple.setUser1Id(1L);
        boundCouple.setUser2Id(2L);
        boundCouple.setStatus(1);
        boundCouple.setStartDate(LocalDate.now().minusDays(100));

        when(userMapper.selectById(1L)).thenReturn(user1);
        when(coupleMapper.selectById(1L)).thenReturn(boundCouple);
        when(coupleMapper.updateById(any(Couple.class))).thenReturn(1);

        // When
        coupleService.applyUnbind(1L, new com.aicoupledish.domain.req.UnbindReq());

        // Then
        verify(coupleMapper).updateById(argThat(couple ->
            couple.getStatus() == 3));
    }

    @Test
    @DisplayName("确认解绑-应清除情侣关系")
    void confirmUnbind_ShouldClearCoupleRelation() {
        // Given
        Couple applyingCouple = new Couple();
        applyingCouple.setId(1L);
        applyingCouple.setUser1Id(1L);
        applyingCouple.setUser2Id(2L);
        applyingCouple.setStatus(3);
        applyingCouple.setUnbindApplicantId(1L);
        applyingCouple.setStartDate(LocalDate.now().minusDays(100));

        when(coupleMapper.selectById(1L)).thenReturn(applyingCouple);
        when(userMapper.selectById(1L)).thenReturn(user1);
        when(userMapper.selectById(2L)).thenReturn(user2);
        when(coupleMapper.updateById(any(Couple.class))).thenReturn(1);
        when(userMapper.updateById(any(User.class))).thenReturn(1);

        // When
        coupleService.confirmUnbind(2L, 1L);

        // Then
        verify(coupleMapper).updateById(argThat(couple ->
            couple.getStatus() == 2));
    }

    @Test
    @DisplayName("拒绝解绑-应恢复绑定状态")
    void rejectUnbind_ShouldRestoreStatus() {
        // Given
        Couple applyingCouple = new Couple();
        applyingCouple.setId(1L);
        applyingCouple.setUser1Id(1L);
        applyingCouple.setUser2Id(2L);
        applyingCouple.setStatus(3);
        applyingCouple.setUnbindApplicantId(1L);
        applyingCouple.setStartDate(LocalDate.now().minusDays(100));

        when(coupleMapper.selectById(1L)).thenReturn(applyingCouple);
        when(coupleMapper.updateById(any(Couple.class))).thenReturn(1);

        // When
        coupleService.rejectUnbind(2L, 1L);

        // Then
        verify(coupleMapper).updateById(argThat(couple ->
            couple.getStatus() == 1));
    }

    @Test
    @DisplayName("获取恋爱计时-已绑定应返回计时信息")
    void getLoveTimer_BoundCouple_ShouldReturnTimer() {
        // Given
        user1.setCoupleId(1L);
        user1.setLoveStartDate(LocalDateTime.of(2025, 11, 11, 0, 0, 0));

        when(userMapper.selectById(1L)).thenReturn(user1);
        when(coupleMapper.selectById(1L)).thenReturn(testCouple);

        // When
        var result = coupleService.getLoveTimer(1L);

        // Then
        assertNotNull(result);
    }

    @Test
    @DisplayName("获取情侣主页-已绑定应返回完整信息")
    void getCoupleHome_BoundCouple_ShouldReturnFullInfo() {
        // Given
        user1.setCoupleId(1L);
        user1.setLoveStartDate(LocalDateTime.of(2025, 11, 11, 0, 0, 0));

        when(userMapper.selectById(1L)).thenReturn(user1);
        when(userMapper.selectById(2L)).thenReturn(user2);
        when(coupleMapper.selectById(1L)).thenReturn(testCouple);

        // When
        var result = coupleService.getCoupleHome(1L);

        // Then
        assertNotNull(result);
        assertNotNull(result.getMyInfo());
        assertNotNull(result.getPartnerInfo());
        assertTrue(result.getLoveDays() >= 0);
    }

    @Test
    @DisplayName("申请解绑-未绑定应抛异常")
    void applyUnbind_NotBound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(3L)).thenReturn(unboundUser);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> coupleService.applyUnbind(3L, new com.aicoupledish.domain.req.UnbindReq()));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("确认解绑-情侣不存在应抛异常")
    void confirmUnbind_CoupleNotFound_ShouldThrowException() {
        // Given
        when(coupleMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> coupleService.confirmUnbind(2L, 999L));
        assertEquals(BusinessException.COUPLE_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("拒绝解绑-情侣不存在应抛异常")
    void rejectUnbind_CoupleNotFound_ShouldThrowException() {
        // Given
        when(coupleMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> coupleService.rejectUnbind(2L, 999L));
        assertEquals(BusinessException.COUPLE_NOT_FOUND.getCode(), exception.getCode());
    }
}
