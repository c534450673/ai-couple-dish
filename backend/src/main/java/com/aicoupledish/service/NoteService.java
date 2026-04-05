package com.aicoupledish.service;

import com.aicoupledish.domain.dto.FoodNoteDTO;
import com.aicoupledish.domain.req.AddNoteReq;

import java.util.List;

/**
 * 笔记服务接口
 */
public interface NoteService {

    /**
     * 获取笔记列表
     */
    List<FoodNoteDTO> getNoteList(Long userId, Long anniversaryId);

    /**
     * 获取笔记详情
     */
    FoodNoteDTO getNoteDetail(Long userId, Long noteId);

    /**
     * 添加笔记
     */
    Long addNote(Long userId, AddNoteReq req);

    /**
     * 更新笔记
     */
    void updateNote(Long userId, Long noteId, AddNoteReq req);

    /**
     * 删除笔记
     */
    void deleteNote(Long userId, Long noteId);

    /**
     * 点赞笔记
     */
    void likeNote(Long userId, Long noteId);

    /**
     * 取消点赞
     */
    void unlikeNote(Long userId, Long noteId);

    /**
     * 评论笔记
     */
    void commentNote(Long userId, Long noteId, String content);

    /**
     * 增加浏览次数
     */
    void incrementViewCount(Long noteId);
}