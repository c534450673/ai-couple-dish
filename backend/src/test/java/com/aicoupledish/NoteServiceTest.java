package com.aicoupledish;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.AnniversaryMapper;
import com.aicoupledish.dao.mapper.FoodNoteMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Anniversary;
import com.aicoupledish.dao.model.FoodNote;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.FoodNoteDTO;
import com.aicoupledish.domain.req.AddNoteReq;
import com.aicoupledish.service.impl.NoteServiceImpl;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 笔记服务单元测试
 * 测试范围：笔记CRUD、点赞、评论、浏览量统计
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("笔记服务测试")
class NoteServiceTest {

    @Mock
    private FoodNoteMapper noteMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private AnniversaryMapper anniversaryMapper;

    @InjectMocks
    private NoteServiceImpl noteService;

    private User testUser;
    private User testPartner;
    private FoodNote testNote;
    private Anniversary testAnniversary;

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

        // 初始化测试笔记
        testNote = new FoodNote();
        testNote.setId(1L);
        testNote.setCoupleId(1L);
        testNote.setAuthorId(1L);
        testNote.setTitle("第一次约会餐厅推荐");
        testNote.setContent("今天去了太二酸菜鱼，味道真的很不错...");
        testNote.setLocation("深圳市南山区科兴科学园");
        testNote.setLatitude(BigDecimal.valueOf(22.5431));
        testNote.setLongitude(BigDecimal.valueOf(113.9416));
        testNote.setIsAnniversaryLinked(0);
        testNote.setViewCount(100);
        testNote.setLikeCount(10);
        testNote.setCommentCount(5);
        testNote.setPhotoUrls("[\"https://example.com/photo1.jpg\"]");
        testNote.setCreateTime(LocalDateTime.now());

        // 初始化纪念日
        testAnniversary = new Anniversary();
        testAnniversary.setId(1L);
        testAnniversary.setCoupleId(1L);
        testAnniversary.setName("恋爱纪念日");
    }

    @Test
    @DisplayName("获取笔记列表-未绑定情侣应抛异常")
    void getNoteList_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> noteService.getNoteList(99L, null));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取笔记列表-有笔记应返回列表")
    void getNoteList_WithNotes_ShouldReturnList() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testNote));

        // When
        List<FoodNoteDTO> result = noteService.getNoteList(1L, null);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("第一次约会餐厅推荐", result.get(0).getTitle());
    }

    @Test
    @DisplayName("获取笔记列表-按纪念日筛选")
    void getNoteList_FilterByAnniversary_ShouldReturnFilteredList() {
        // Given
        testNote.setAnniversaryId(1L);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Arrays.asList(testNote));

        // When
        List<FoodNoteDTO> result = noteService.getNoteList(1L, 1L);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
    }

    @Test
    @DisplayName("获取笔记列表-空列表")
    void getNoteList_EmptyList_ShouldReturnEmptyList() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectList(any(LambdaQueryWrapper.class)))
            .thenReturn(Collections.emptyList());

        // When
        List<FoodNoteDTO> result = noteService.getNoteList(1L, null);

        // Then
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("获取笔记详情-笔记存在应返回详情")
    void getNoteDetail_NoteExists_ShouldReturnDetail() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(1L)).thenReturn(testNote);

        // When
        FoodNoteDTO result = noteService.getNoteDetail(1L, 1L);

        // Then
        assertNotNull(result);
        assertEquals(1L, result.getId());
        assertEquals("第一次约会餐厅推荐", result.getTitle());
        assertEquals("小明", result.getAuthorName());
    }

    @Test
    @DisplayName("获取笔记详情-笔记不存在应抛异常")
    void getNoteDetail_NoteNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(999L)).thenReturn(null);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> noteService.getNoteDetail(1L, 999L));
        assertEquals(BusinessException.NOTE_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("获取笔记详情-无权限应抛异常")
    void getNoteDetail_NoPermission_ShouldThrowException() {
        // Given
        User otherUser = new User();
        otherUser.setId(3L);
        otherUser.setCoupleId(2L); // 不同的情侣ID
        otherUser.setStatus(0);

        when(userMapper.selectById(3L)).thenReturn(otherUser);
        when(noteMapper.selectById(1L)).thenReturn(testNote);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> noteService.getNoteDetail(3L, 1L));
        assertEquals(BusinessException.NOTE_NOT_PERMISSION.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("添加笔记-未绑定情侣应抛异常")
    void addNote_NotBindCouple_ShouldThrowException() {
        // Given
        User unboundUser = new User();
        unboundUser.setId(99L);
        unboundUser.setCoupleId(null);
        when(userMapper.selectById(99L)).thenReturn(unboundUser);

        AddNoteReq req = new AddNoteReq();
        req.setTitle("测试笔记");
        req.setContent("测试内容");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> noteService.addNote(99L, req));
        assertEquals(BusinessException.COUPLE_NOT_BIND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("添加笔记-完整信息应成功")
    void addNote_FullInfo_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.insert(any(FoodNote.class))).thenReturn(1);

        AddNoteReq req = new AddNoteReq();
        req.setTitle("新的美食笔记");
        req.setContent("今天尝试了一家新餐厅...");
        req.setLocation("深圳市南山区");
        req.setLatitude(22.5431);
        req.setLongitude(113.9416);
        req.setIsAnniversaryLinked(1);
        req.setAnniversaryId(1L);
        req.setPhotoUrls(Arrays.asList("https://example.com/photo1.jpg", "https://example.com/photo2.jpg"));

        // When
        Long noteId = noteService.addNote(1L, req);

        // Then
        assertNotNull(noteId);
        verify(noteMapper).insert(any(FoodNote.class));
    }

    @Test
    @DisplayName("添加笔记-基础信息应成功")
    void addNote_BasicInfo_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.insert(any(FoodNote.class))).thenReturn(1);

        AddNoteReq req = new AddNoteReq();
        req.setTitle("简单笔记");
        req.setContent("今天吃得很开心");

        // When
        Long noteId = noteService.addNote(1L, req);

        // Then
        assertNotNull(noteId);
        verify(noteMapper).insert(any(FoodNote.class));
    }

    @Test
    @DisplayName("更新笔记-作者本人应成功")
    void updateNote_Author_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(noteMapper.updateById(any(FoodNote.class))).thenReturn(1);

        AddNoteReq req = new AddNoteReq();
        req.setTitle("更新后的标题");
        req.setContent("更新后的内容");

        // When
        noteService.updateNote(1L, 1L, req);

        // Then
        verify(noteMapper).updateById(any(FoodNote.class));
    }

    @Test
    @DisplayName("更新笔记-非作者应抛异常")
    void updateNote_NotAuthor_ShouldThrowException() {
        // Given
        when(userMapper.selectById(2L)).thenReturn(testPartner);
        when(noteMapper.selectById(1L)).thenReturn(testNote);

        AddNoteReq req = new AddNoteReq();
        req.setTitle("尝试修改");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> noteService.updateNote(2L, 1L, req));
        assertEquals(BusinessException.NOTE_NOT_PERMISSION.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("更新笔记-笔记不存在应抛异常")
    void updateNote_NoteNotFound_ShouldThrowException() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(999L)).thenReturn(null);

        AddNoteReq req = new AddNoteReq();
        req.setTitle("测试");

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> noteService.updateNote(1L, 999L, req));
        assertEquals(BusinessException.NOTE_NOT_FOUND.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("删除笔记-作者本人应成功")
    void deleteNote_Author_ShouldSuccess() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(noteMapper.deleteById(1L)).thenReturn(1);

        // When
        noteService.deleteNote(1L, 1L);

        // Then
        verify(noteMapper).deleteById(1L);
    }

    @Test
    @DisplayName("删除笔记-非作者应抛异常")
    void deleteNote_NotAuthor_ShouldThrowException() {
        // Given
        when(userMapper.selectById(2L)).thenReturn(testPartner);
        when(noteMapper.selectById(1L)).thenReturn(testNote);

        // When & Then
        BusinessException exception = assertThrows(BusinessException.class,
            () -> noteService.deleteNote(2L, 1L));
        assertEquals(BusinessException.NOTE_NOT_PERMISSION.getCode(), exception.getCode());
    }

    @Test
    @DisplayName("点赞笔记-笔记存在应成功")
    void likeNote_NoteExists_ShouldSuccess() {
        // Given
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(noteMapper.updateById(any(FoodNote.class))).thenReturn(1);

        // When
        noteService.likeNote(2L, 1L); // 用户2点赞

        // Then
        verify(noteMapper).updateById(argThat(note ->
            note.getLikeCount() == 11)); // 10 + 1
    }

    @Test
    @DisplayName("点赞笔记-点赞数从0开始")
    void likeNote_FromZero_ShouldSuccess() {
        // Given
        testNote.setLikeCount(0);
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(noteMapper.updateById(any(FoodNote.class))).thenReturn(1);

        // When
        noteService.likeNote(2L, 1L);

        // Then
        verify(noteMapper).updateById(argThat(note ->
            note.getLikeCount() == 1));
    }

    @Test
    @DisplayName("取消点赞-点赞数应减少")
    void unlikeNote_ShouldDecrementLikeCount() {
        // Given
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(noteMapper.updateById(any(FoodNote.class))).thenReturn(1);

        // When
        noteService.unlikeNote(2L, 1L);

        // Then
        verify(noteMapper).updateById(argThat(note ->
            note.getLikeCount() == 9)); // 10 - 1
    }

    @Test
    @DisplayName("评论笔记-笔记存在应成功")
    void commentNote_NoteExists_ShouldSuccess() {
        // Given
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(noteMapper.updateById(any(FoodNote.class))).thenReturn(1);

        // When
        noteService.commentNote(2L, 1L, "写得真好！");

        // Then
        verify(noteMapper).updateById(argThat(note ->
            note.getCommentCount() == 6)); // 5 + 1
    }

    @Test
    @DisplayName("增加浏览量-笔记存在应成功")
    void incrementViewCount_NoteExists_ShouldSuccess() {
        // Given
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(noteMapper.updateById(any(FoodNote.class))).thenReturn(1);

        // When
        noteService.incrementViewCount(1L);

        // Then
        verify(noteMapper).updateById(argThat(note ->
            note.getViewCount() == 101)); // 100 + 1
    }

    @Test
    @DisplayName("笔记详情应包含作者信息")
    void noteDetail_ShouldIncludeAuthorInfo() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(1L)).thenReturn(testNote);

        // When
        FoodNoteDTO result = noteService.getNoteDetail(1L, 1L);

        // Then
        assertNotNull(result.getAuthorName());
        assertEquals("小明", result.getAuthorName());
        assertNotNull(result.getAuthorAvatar());
    }

    @Test
    @DisplayName("笔记详情应包含纪念日名称")
    void noteDetail_ShouldIncludeAnniversaryName() {
        // Given
        testNote.setAnniversaryId(1L);
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(1L)).thenReturn(testNote);
        when(anniversaryMapper.selectById(1L)).thenReturn(testAnniversary);

        // When
        FoodNoteDTO result = noteService.getNoteDetail(1L, 1L);

        // Then
        assertNotNull(result.getAnniversaryName());
        assertEquals("恋爱纪念日", result.getAnniversaryName());
    }

    @Test
    @DisplayName("笔记应正确解析照片URL列表")
    void noteDetail_ShouldParsePhotoUrls() {
        // Given
        when(userMapper.selectById(1L)).thenReturn(testUser);
        when(noteMapper.selectById(1L)).thenReturn(testNote);

        // When
        FoodNoteDTO result = noteService.getNoteDetail(1L, 1L);

        // Then
        assertNotNull(result.getPhotoUrls());
        assertEquals(1, result.getPhotoUrls().size());
        assertEquals("https://example.com/photo1.jpg", result.getPhotoUrls().get(0));
    }
}
