package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.CoupleMapper;
import com.aicoupledish.dao.mapper.TimeCapsuleMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Couple;
import com.aicoupledish.dao.model.TimeCapsule;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.TimeCapsuleDTO;
import com.aicoupledish.domain.req.TimeCapsuleReq;
import com.aicoupledish.service.impl.TimeCapsuleServiceImpl;
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
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 时光胶囊服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("时光胶囊服务测试")
class TimeCapsuleServiceTest {

    @Mock
    private TimeCapsuleMapper timeCapsuleMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private TimeCapsuleServiceImpl timeCapsuleService;

    private User testUser;
    private User partnerUser;
    private Couple testCouple;
    private TimeCapsule testCapsule;
    private TimeCapsuleReq capsuleReq;

    @BeforeEach
    void setUp() {
        testUser = new User();
        testUser.setId(1L);
        testUser.setNickName("用户1");
        testUser.setAvatarUrl("https://example.com/avatar1.jpg");
        testUser.setCoupleId(1L);

        partnerUser = new User();
        partnerUser.setId(2L);
        partnerUser.setNickName("用户2");
        partnerUser.setAvatarUrl("https://example.com/avatar2.jpg");

        testCouple = new Couple();
        testCouple.setId(1L);
        testCouple.setUser1Id(1L);
        testCouple.setUser2Id(2L);
        testCouple.setStatus(1);

        testCapsule = new TimeCapsule();
        testCapsule.setId(1L);
        testCapsule.setCoupleId(1L);
        testCapsule.setCreatorId(1L);
        testCapsule.setCapsuleType("text");
        testCapsule.setTitle("测试胶囊");
        testCapsule.setContent("这是测试内容");
        testCapsule.setUnlockDate(LocalDate.now().plusDays(7));
        testCapsule.setStatus(0);
        testCapsule.setCreateTime(LocalDateTime.now());

        capsuleReq = new TimeCapsuleReq();
        capsuleReq.setCapsuleType("text");
        capsuleReq.setTitle("测试胶囊");
        capsuleReq.setContent("这是测试内容");
        capsuleReq.setUnlockDate(LocalDate.now().plusDays(7));
    }

    @Nested
    @DisplayName("创建时光胶囊测试")
    class CreateTimeCapsuleTests {

        @Test
        @DisplayName("创建时光胶囊-成功")
        void createTimeCapsule_Success() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(timeCapsuleMapper.insert(any(TimeCapsule.class))).thenAnswer(invocation -> {
                TimeCapsule capsule = invocation.getArgument(0);
                capsule.setId(1L);
                return 1;
            });

            // When
            Long capsuleId = timeCapsuleService.createTimeCapsule(1L, capsuleReq);

            // Then
            assertNotNull(capsuleId);
            verify(timeCapsuleMapper).insert(any(TimeCapsule.class));
        }

        @Test
        @DisplayName("创建时光胶囊-用户未绑定应抛异常")
        void createTimeCapsule_NotBound_ThrowsException() {
            // Given
            testUser.setCoupleId(null);
            when(userMapper.selectById(1L)).thenReturn(testUser);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> timeCapsuleService.createTimeCapsule(1L, capsuleReq));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
        }

        @Test
        @DisplayName("创建时光胶囊-解锁日期过早应抛异常")
        void createTimeCapsule_PastUnlockDate_ThrowsException() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            capsuleReq.setUnlockDate(LocalDate.now());

            // When & Then
            assertThrows(IllegalArgumentException.class,
                () -> timeCapsuleService.createTimeCapsule(1L, capsuleReq));
        }
    }

    @Nested
    @DisplayName("获取时光胶囊列表测试")
    class GetTimeCapsuleListTests {

        @Test
        @DisplayName("获取时光胶囊列表-成功")
        void getTimeCapsuleList_Success() {
            // Given
            List<TimeCapsule> capsules = new ArrayList<>();
            capsules.add(testCapsule);
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(timeCapsuleMapper.selectList(any())).thenReturn(capsules);
            when(userMapper.selectById(1L)).thenReturn(testUser);

            // When
            List<TimeCapsuleDTO> result = timeCapsuleService.getTimeCapsuleList(1L);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
        }

        @Test
        @DisplayName("获取时光胶囊列表-用户未绑定应抛异常")
        void getTimeCapsuleList_NotBound_ThrowsException() {
            // Given
            testUser.setCoupleId(null);
            when(userMapper.selectById(1L)).thenReturn(testUser);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> timeCapsuleService.getTimeCapsuleList(1L));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
        }
    }

    @Nested
    @DisplayName("解锁时光胶囊测试")
    class UnlockTimeCapsuleTests {

        @Test
        @DisplayName("解锁时光胶囊-成功")
        void unlockTimeCapsule_Success() {
            // Given
            testCapsule.setUnlockDate(LocalDate.now());
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(timeCapsuleMapper.selectById(1L)).thenReturn(testCapsule);
            when(timeCapsuleMapper.updateById(any(TimeCapsule.class))).thenReturn(1);

            // When
            TimeCapsuleDTO result = timeCapsuleService.unlockTimeCapsule(1L, 1L);

            // Then
            assertNotNull(result);
            assertEquals(1, result.getStatus());
            verify(timeCapsuleMapper).updateById(argThat(c -> c.getStatus() == 1));
        }

        @Test
        @DisplayName("解锁时光胶囊-胶囊不存在应抛异常")
        void unlockTimeCapsule_NotFound_ThrowsException() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(timeCapsuleMapper.selectById(999L)).thenReturn(null);

            // When & Then
            assertThrows(IllegalArgumentException.class,
                () -> timeCapsuleService.unlockTimeCapsule(1L, 999L));
        }

        @Test
        @DisplayName("解锁时光胶囊-未到解锁日期应抛异常")
        void unlockTimeCapsule_NotYetTime_ThrowsException() {
            // Given
            testCapsule.setUnlockDate(LocalDate.now().plusDays(7));
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(timeCapsuleMapper.selectById(1L)).thenReturn(testCapsule);

            // When & Then
            assertThrows(IllegalArgumentException.class,
                () -> timeCapsuleService.unlockTimeCapsule(1L, 1L));
        }

        @Test
        @DisplayName("解锁时光胶囊-已解锁应抛异常")
        void unlockTimeCapsule_AlreadyUnlocked_ThrowsException() {
            // Given
            testCapsule.setStatus(1);
            testCapsule.setUnlockDate(LocalDate.now());
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(timeCapsuleMapper.selectById(1L)).thenReturn(testCapsule);

            // When & Then
            assertThrows(IllegalArgumentException.class,
                () -> timeCapsuleService.unlockTimeCapsule(1L, 1L));
        }
    }

    @Nested
    @DisplayName("删除时光胶囊测试")
    class DeleteTimeCapsuleTests {

        @Test
        @DisplayName("删除时光胶囊-成功")
        void deleteTimeCapsule_Success() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            when(timeCapsuleMapper.selectById(1L)).thenReturn(testCapsule);
            when(timeCapsuleMapper.deleteById(1L)).thenReturn(1);

            // When
            assertDoesNotThrow(() -> timeCapsuleService.deleteTimeCapsule(1L, 1L));

            // Then
            verify(timeCapsuleMapper).deleteById(1L);
        }

        @Test
        @DisplayName("删除时光胶囊-非创建者应抛异常")
        void deleteTimeCapsule_NotCreator_ThrowsException() {
            // Given
            when(userMapper.selectById(1L)).thenReturn(testUser);
            testCapsule.setCreatorId(2L);
            when(timeCapsuleMapper.selectById(1L)).thenReturn(testCapsule);

            // When & Then
            BusinessException exception = assertThrows(BusinessException.class,
                () -> timeCapsuleService.deleteTimeCapsule(1L, 1L));
            assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), exception.getCode());
        }
    }
}
