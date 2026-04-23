package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.PosterDTO;
import com.aicoupledish.service.impl.PosterServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 海报服务单元测试
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("海报服务测试")
class PosterServiceTest {

    @Mock
    private PosterTemplateMapper posterTemplateMapper;

    @Mock
    private UserPosterMapper userPosterMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private CoupleMapper coupleMapper;

    @Mock
    private AnniversaryMapper anniversaryMapper;

    @Mock
    private CoupleMenuMapper coupleMenuMapper;

    @Mock
    private FoodNoteMapper foodNoteMapper;

    @InjectMocks
    private PosterServiceImpl posterService;

    private Long userId;
    private Long coupleId;
    private User user;
    private PosterTemplate template;
    private UserPoster userPoster;

    @BeforeEach
    void setUp() {
        userId = 1L;
        coupleId = 100L;

        user = new User();
        user.setId(userId);
        user.setNickName("小明");
        user.setAvatarUrl("/avatar/1.png");
        user.setCoupleId(coupleId);

        template = new PosterTemplate();
        template.setId(1L);
        template.setTemplateCode("anniversary_01");
        template.setTemplateName("纪念日模板1");
        template.setTemplateType("anniversary");
        template.setTemplateConfig("{\"background\":\"#FF6B6B\"}");
        template.setPreviewUrl("/templates/anniversary_01_preview.png");
        template.setIsActive(1);

        userPoster = new UserPoster();
        userPoster.setId(1L);
        userPoster.setUserId(userId);
        userPoster.setCoupleId(coupleId);
        userPoster.setPosterType("anniversary");
        userPoster.setTemplateId(1L);
        userPoster.setPosterUrl("/posters/abc123.png");
        userPoster.setInviteCode("XYZ789");
        userPoster.setCreateTime(LocalDateTime.now());
    }

    @Nested
    @DisplayName("获取模板列表")
    class GetTemplates {

        @Test
        @DisplayName("获取模板列表-成功")
        void getTemplates_success() {
            // Given
            when(posterTemplateMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(template));

            // When
            List<PosterDTO.TemplateDTO> result = posterService.getTemplates("anniversary");

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals("anniversary_01", result.get(0).getTemplateCode());
            assertEquals("纪念日模板1", result.get(0).getTemplateName());
            assertTrue(result.get(0).getIsActive());
        }

        @Test
        @DisplayName("获取模板列表-无模板返回空列表")
        void getTemplates_empty() {
            // Given
            when(posterTemplateMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            List<PosterDTO.TemplateDTO> result = posterService.getTemplates(null);

            // Then
            assertNotNull(result);
            assertTrue(result.isEmpty());
        }

        @Test
        @DisplayName("获取模板列表-模板类型名称正确映射")
        void getTemplates_typeNameMapping() {
            // Given
            template.setTemplateType("feed");
            when(posterTemplateMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(template));

            // When
            List<PosterDTO.TemplateDTO> result = posterService.getTemplates("feed");

            // Then
            assertEquals("恋爱动态海报", result.get(0).getTemplateTypeName());
        }

        @Test
        @DisplayName("获取模板列表-map类型映射为足迹地图海报")
        void getTemplates_mapType() {
            // Given
            template.setTemplateType("map");
            when(posterTemplateMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(template));

            // When
            List<PosterDTO.TemplateDTO> result = posterService.getTemplates("map");

            // Then
            assertEquals("足迹地图海报", result.get(0).getTemplateTypeName());
        }

        @Test
        @DisplayName("获取模板列表-annual类型映射为年度总结海报")
        void getTemplates_annualType() {
            // Given
            template.setTemplateType("annual");
            when(posterTemplateMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(template));

            // When
            List<PosterDTO.TemplateDTO> result = posterService.getTemplates("annual");

            // Then
            assertEquals("年度总结海报", result.get(0).getTemplateTypeName());
        }
    }

    @Nested
    @DisplayName("生成海报")
    class GeneratePoster {

        @Test
        @DisplayName("生成海报-成功")
        void generatePoster_success() {
            // Given
            PosterDTO.GenerateReq req = new PosterDTO.GenerateReq();
            req.setTemplateId(1L);
            req.setPosterType("anniversary");

            when(userMapper.selectById(userId)).thenReturn(user);
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);
            when(userPosterMapper.insert(any(UserPoster.class))).thenReturn(1);
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);

            // When
            PosterDTO result = posterService.generatePoster(userId, req);

            // Then
            assertNotNull(result);
            verify(userPosterMapper).insert(argThat(p ->
                    p.getUserId().equals(userId) &&
                    p.getCoupleId() != null &&
                    p.getPosterType().equals("anniversary") &&
                    p.getInviteCode() != null
            ));
        }

        @Test
        @DisplayName("生成海报-未绑定情侣应抛异常")
        void generatePoster_notBound_throw() {
            // Given
            user.setCoupleId(null);
            PosterDTO.GenerateReq req = new PosterDTO.GenerateReq();
            req.setTemplateId(1L);
            req.setPosterType("anniversary");

            when(userMapper.selectById(userId)).thenReturn(user);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> posterService.generatePoster(userId, req));
            assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), ex.getCode());
        }

        @Test
        @DisplayName("生成海报-模板不存在应抛IllegalArgumentException")
        void generatePoster_templateNotFound_throw() {
            // Given
            PosterDTO.GenerateReq req = new PosterDTO.GenerateReq();
            req.setTemplateId(99L);
            req.setPosterType("anniversary");

            when(userMapper.selectById(userId)).thenReturn(user);
            when(posterTemplateMapper.selectById(99L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> posterService.generatePoster(userId, req));
            assertEquals("模板不存在或已禁用", ex.getMessage());
        }

        @Test
        @DisplayName("生成海报-模板已禁用应抛IllegalArgumentException")
        void generatePoster_templateDisabled_throw() {
            // Given
            template.setIsActive(0);
            PosterDTO.GenerateReq req = new PosterDTO.GenerateReq();
            req.setTemplateId(1L);
            req.setPosterType("anniversary");

            when(userMapper.selectById(userId)).thenReturn(user);
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> posterService.generatePoster(userId, req));
            assertEquals("模板不存在或已禁用", ex.getMessage());
        }

        @Test
        @DisplayName("生成海报-用户不存在应抛异常")
        void generatePoster_userNotFound_throw() {
            // Given
            PosterDTO.GenerateReq req = new PosterDTO.GenerateReq();
            req.setTemplateId(1L);
            req.setPosterType("anniversary");

            when(userMapper.selectById(userId)).thenReturn(null);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> posterService.generatePoster(userId, req));
            assertEquals(BusinessException.USER_NOT_FOUND.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("获取我的海报列表")
    class GetMyPosters {

        @Test
        @DisplayName("获取我的海报-成功")
        void getMyPosters_success() {
            // Given
            when(userPosterMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(userPoster));
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);

            // When
            List<PosterDTO> result = posterService.getMyPosters(userId, "anniversary", 10);

            // Then
            assertNotNull(result);
            assertEquals(1, result.size());
            assertEquals("anniversary", result.get(0).getPosterType());
            assertEquals("纪念日海报", result.get(0).getPosterTypeName());
        }

        @Test
        @DisplayName("获取我的海报-空列表")
        void getMyPosters_empty() {
            // Given
            when(userPosterMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(Collections.emptyList());

            // When
            List<PosterDTO> result = posterService.getMyPosters(userId, null, 20);

            // Then
            assertNotNull(result);
            assertTrue(result.isEmpty());
        }
    }

    @Nested
    @DisplayName("获取海报详情")
    class GetPosterDetail {

        @Test
        @DisplayName("获取海报详情-成功")
        void getPosterDetail_success() {
            // Given
            when(userPosterMapper.selectById(1L)).thenReturn(userPoster);
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);

            // When
            PosterDTO result = posterService.getPosterDetail(userId, 1L);

            // Then
            assertNotNull(result);
            assertEquals("/posters/abc123.png", result.getPosterUrl());
        }

        @Test
        @DisplayName("获取海报详情-海报不存在应抛IllegalArgumentException")
        void getPosterDetail_notFound_throw() {
            // Given
            when(userPosterMapper.selectById(99L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> posterService.getPosterDetail(userId, 99L));
            assertEquals("海报不存在", ex.getMessage());
        }

        @Test
        @DisplayName("获取海报详情-无权查看应抛异常")
        void getPosterDetail_noPermission_throw() {
            // Given
            userPoster.setUserId(999L); // different user
            when(userPosterMapper.selectById(1L)).thenReturn(userPoster);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> posterService.getPosterDetail(userId, 1L));
            assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("删除海报")
    class DeletePoster {

        @Test
        @DisplayName("删除海报-成功")
        void deletePoster_success() {
            // Given
            when(userPosterMapper.selectById(1L)).thenReturn(userPoster);
            when(userPosterMapper.deleteById(1L)).thenReturn(1);

            // When
            posterService.deletePoster(userId, 1L);

            // Then
            verify(userPosterMapper).deleteById(1L);
        }

        @Test
        @DisplayName("删除海报-海报不存在应抛IllegalArgumentException")
        void deletePoster_notFound_throw() {
            // Given
            when(userPosterMapper.selectById(99L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> posterService.deletePoster(userId, 99L));
            assertEquals("海报不存在", ex.getMessage());
        }

        @Test
        @DisplayName("删除海报-无权删除应抛异常")
        void deletePoster_noPermission_throw() {
            // Given
            userPoster.setUserId(999L);
            when(userPosterMapper.selectById(1L)).thenReturn(userPoster);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> posterService.deletePoster(userId, 1L));
            assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("获取海报分享数据")
    class GetPosterShareData {

        @Test
        @DisplayName("获取海报分享数据-成功")
        void getPosterShareData_success() {
            // Given
            when(userPosterMapper.selectById(1L)).thenReturn(userPoster);
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);

            // When
            PosterDTO result = posterService.getPosterShareData(userId, 1L);

            // Then
            assertNotNull(result);
            assertEquals("XYZ789", result.getInviteCode());
        }

        @Test
        @DisplayName("获取海报分享数据-海报不存在应抛IllegalArgumentException")
        void getPosterShareData_notFound_throw() {
            // Given
            when(userPosterMapper.selectById(99L)).thenReturn(null);

            // When & Then
            IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                    () -> posterService.getPosterShareData(userId, 99L));
            assertEquals("海报不存在", ex.getMessage());
        }

        @Test
        @DisplayName("获取海报分享数据-无权查看应抛异常")
        void getPosterShareData_noPermission_throw() {
            // Given
            userPoster.setUserId(999L);
            when(userPosterMapper.selectById(1L)).thenReturn(userPoster);

            // When & Then
            BusinessException ex = assertThrows(BusinessException.class,
                    () -> posterService.getPosterShareData(userId, 1L));
            assertEquals(BusinessException.MENU_NOT_PERMISSION.getCode(), ex.getCode());
        }
    }

    @Nested
    @DisplayName("海报类型名称映射")
    class PosterTypeNameMapping {

        @Test
        @DisplayName("anniversary类型映射为纪念日海报")
        void typeName_anniversary() {
            // Given
            when(userPosterMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(userPoster));
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);

            // When
            List<PosterDTO> result = posterService.getMyPosters(userId, null, 10);

            // Then
            assertEquals("纪念日海报", result.get(0).getPosterTypeName());
        }

        @Test
        @DisplayName("未知类型原样返回")
        void typeName_unknown() {
            // Given
            userPoster.setPosterType("custom");
            when(userPosterMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(List.of(userPoster));
            when(posterTemplateMapper.selectById(1L)).thenReturn(template);

            // When
            List<PosterDTO> result = posterService.getMyPosters(userId, null, 10);

            // Then
            assertEquals("custom", result.get(0).getPosterTypeName());
        }
    }
}
