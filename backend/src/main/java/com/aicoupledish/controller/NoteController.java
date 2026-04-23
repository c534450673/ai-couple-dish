package com.aicoupledish.controller;

import com.aicoupledish.common.utils.JwtUtils;
import com.aicoupledish.common.utils.Result;
import com.aicoupledish.domain.dto.FoodNoteDTO;
import com.aicoupledish.domain.req.AddNoteReq;
import com.aicoupledish.service.NoteService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;

/**
 * 笔记控制器
 */
@Api(tags = "笔记模块")
@RestController
@RequestMapping("/note")
@RequiredArgsConstructor
public class NoteController extends BaseAuthController {

    private final NoteService noteService;
    private final JwtUtils jwtUtils;

    private final HttpServletRequest request;

    @ApiOperation("获取笔记列表")
    @GetMapping("/list")
    public Result<List<FoodNoteDTO>> getNoteList(@RequestParam(required = false) Long anniversaryId) {
        Long userId = getCurrentUserId(request, jwtUtils);
        List<FoodNoteDTO> list = noteService.getNoteList(userId, anniversaryId);
        return Result.success(list);
    }

    @ApiOperation("获取笔记详情")
    @GetMapping("/detail/{id}")
    public Result<FoodNoteDTO> getNoteDetail(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        FoodNoteDTO note = noteService.getNoteDetail(userId, id);
        return Result.success(note);
    }

    @ApiOperation("添加笔记")
    @PostMapping("/add")
    public Result<Long> addNote(@Valid @RequestBody AddNoteReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        Long noteId = noteService.addNote(userId, req);
        return Result.success("笔记添加成功", noteId);
    }

    @ApiOperation("更新笔记")
    @PutMapping("/update/{id}")
    public Result<Void> updateNote(@PathVariable Long id, @RequestBody AddNoteReq req) {
        Long userId = getCurrentUserId(request, jwtUtils);
        noteService.updateNote(userId, id, req);
        return Result.success();
    }

    @ApiOperation("删除笔记")
    @DeleteMapping("/delete/{id}")
    public Result<Void> deleteNote(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        noteService.deleteNote(userId, id);
        return Result.success();
    }

    @ApiOperation("点赞笔记")
    @PostMapping("/like/{id}")
    public Result<Void> likeNote(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        noteService.likeNote(userId, id);
        return Result.success();
    }

    @ApiOperation("取消点赞")
    @DeleteMapping("/unlike/{id}")
    public Result<Void> unlikeNote(@PathVariable Long id) {
        Long userId = getCurrentUserId(request, jwtUtils);
        noteService.unlikeNote(userId, id);
        return Result.success();
    }

    @ApiOperation("评论笔记")
    @PostMapping("/comment/{id}")
    public Result<Void> commentNote(
            @PathVariable Long id,
            @RequestParam String content) {
        Long userId = getCurrentUserId(request, jwtUtils);
        noteService.commentNote(userId, id, content);
        return Result.success();
    }

}