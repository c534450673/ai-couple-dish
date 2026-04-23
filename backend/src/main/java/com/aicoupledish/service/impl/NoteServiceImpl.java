package com.aicoupledish.service.impl;

import cn.hutool.json.JSONUtil;
import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.common.utils.XssUtils;
import com.aicoupledish.dao.mapper.AnniversaryMapper;
import com.aicoupledish.dao.mapper.FoodNoteMapper;
import com.aicoupledish.dao.mapper.NoteLikeMapper;
import com.aicoupledish.dao.mapper.UserMapper;
import com.aicoupledish.dao.model.Anniversary;
import com.aicoupledish.dao.model.FoodNote;
import com.aicoupledish.dao.model.NoteLike;
import com.aicoupledish.dao.model.User;
import com.aicoupledish.domain.dto.FoodNoteDTO;
import com.aicoupledish.domain.req.AddNoteReq;
import com.aicoupledish.service.NoteService;
import com.aicoupledish.service.NotificationService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 笔记服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NoteServiceImpl implements NoteService {

    private final FoodNoteMapper noteMapper;
    private final UserMapper userMapper;
    private final AnniversaryMapper anniversaryMapper;
    private final NoteLikeMapper noteLikeMapper;

    @Autowired(required = false)
    private NotificationService notificationService;

    @Override
    public List<FoodNoteDTO> getNoteList(Long userId, Long anniversaryId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        LambdaQueryWrapper<FoodNote> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(FoodNote::getCoupleId, user.getCoupleId());
        if (anniversaryId != null) {
            queryWrapper.eq(FoodNote::getAnniversaryId, anniversaryId);
        }
        queryWrapper.orderByDesc(FoodNote::getCreateTime);

        List<FoodNote> notes = noteMapper.selectList(queryWrapper);
        if (notes.isEmpty()) {
            return new ArrayList<>();
        }

        // 批量加载用户信息（修复N+1查询）
        Set<Long> authorIds = notes.stream()
                .map(FoodNote::getAuthorId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = authorIds.isEmpty() ? Collections.emptyMap() :
                userMapper.selectBatchIds(authorIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u, (a, b) -> a));

        // 批量加载纪念日信息（修复N+1查询）
        Set<Long> anniversaryIds = notes.stream()
                .map(FoodNote::getAnniversaryId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<Long, Anniversary> anniversaryMap = anniversaryIds.isEmpty() ? Collections.emptyMap() :
                anniversaryMapper.selectBatchIds(anniversaryIds).stream()
                        .collect(Collectors.toMap(Anniversary::getId, a -> a, (a, b) -> a));

        return notes.stream()
                .map(note -> buildNoteDTOWithCache(note, userMap, anniversaryMap))
                .collect(Collectors.toList());
    }

    @Override
    public FoodNoteDTO getNoteDetail(Long userId, Long noteId) {
        User user = getUserById(userId);
        FoodNote note = noteMapper.selectById(noteId);

        if (note == null) {
            throw BusinessException.NOTE_NOT_FOUND;
        }

        if (!note.getCoupleId().equals(user.getCoupleId())) {
            throw BusinessException.NOTE_NOT_PERMISSION;
        }

        return buildNoteDTO(note);
    }

    @Override
    @Transactional
    public Long addNote(Long userId, AddNoteReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        FoodNote note = new FoodNote();
        note.setCoupleId(user.getCoupleId());
        note.setAuthorId(userId);
        note.setTitle(XssUtils.sanitizePlainText(req.getTitle()));
        note.setContent(XssUtils.sanitizeUserInput(req.getContent()));
        note.setLocation(XssUtils.sanitizePlainText(req.getLocation()));
        note.setLatitude(req.getLatitude() != null ? java.math.BigDecimal.valueOf(req.getLatitude()) : null);
        note.setLongitude(req.getLongitude() != null ? java.math.BigDecimal.valueOf(req.getLongitude()) : null);
        note.setIsAnniversaryLinked(req.getIsAnniversaryLinked() != null ? req.getIsAnniversaryLinked() : 0);
        note.setAnniversaryId(req.getAnniversaryId());
        note.setViewCount(0);
        note.setLikeCount(0);
        note.setCommentCount(0);
        note.setPhotoUrls(req.getPhotoUrls() != null ? JSONUtil.toJsonStr(req.getPhotoUrls()) : null);

        noteMapper.insert(note);

        // 发送通知给伴侣
        if (notificationService != null) {
            Long partnerId = getPartnerId(user);
            if (partnerId != null) {
                notificationService.sendNotification(partnerId, 2, "📝 新笔记",
                    "你的伴侣发布了新笔记：「" + req.getTitle() + "」", note.getId(), "note");
            }
        }

        log.info("添加笔记: userId={}, noteId={}", userId, note.getId());
        return note.getId();
    }

    @Override
    @Transactional
    public void updateNote(Long userId, Long noteId, AddNoteReq req) {
        User user = getUserById(userId);
        FoodNote note = noteMapper.selectById(noteId);

        if (note == null) {
            throw BusinessException.NOTE_NOT_FOUND;
        }

        if (!note.getAuthorId().equals(userId)) {
            throw BusinessException.NOTE_NOT_PERMISSION;
        }

        if (req.getTitle() != null) {
            note.setTitle(XssUtils.sanitizePlainText(req.getTitle()));
        }
        if (req.getContent() != null) {
            note.setContent(XssUtils.sanitizeUserInput(req.getContent()));
        }
        if (req.getLocation() != null) {
            note.setLocation(XssUtils.sanitizePlainText(req.getLocation()));
        }
        if (req.getLatitude() != null) {
            note.setLatitude(java.math.BigDecimal.valueOf(req.getLatitude()));
        }
        if (req.getLongitude() != null) {
            note.setLongitude(java.math.BigDecimal.valueOf(req.getLongitude()));
        }
        if (req.getIsAnniversaryLinked() != null) {
            note.setIsAnniversaryLinked(req.getIsAnniversaryLinked());
        }
        if (req.getAnniversaryId() != null) {
            note.setAnniversaryId(req.getAnniversaryId());
        }
        if (req.getPhotoUrls() != null) {
            note.setPhotoUrls(JSONUtil.toJsonStr(req.getPhotoUrls()));
        }

        noteMapper.updateById(note);
        log.info("更新笔记: userId={}, noteId={}", userId, noteId);
    }

    @Override
    @Transactional
    public void deleteNote(Long userId, Long noteId) {
        User user = getUserById(userId);
        FoodNote note = noteMapper.selectById(noteId);

        if (note == null) {
            throw BusinessException.NOTE_NOT_FOUND;
        }

        if (!note.getAuthorId().equals(userId)) {
            throw BusinessException.NOTE_NOT_PERMISSION;
        }

        noteMapper.deleteById(noteId);
        log.info("删除笔记: userId={}, noteId={}", userId, noteId);
    }

    @Override
    @Transactional
    public void likeNote(Long userId, Long noteId) {
        FoodNote note = noteMapper.selectById(noteId);
        if (note == null) {
            throw BusinessException.NOTE_NOT_FOUND;
        }

        // 检查是否已点赞（幂等性保证）
        NoteLike existingLike = noteLikeMapper.selectOne(
            new LambdaQueryWrapper<NoteLike>()
                .eq(NoteLike::getUserId, userId)
                .eq(NoteLike::getNoteId, noteId)
        );

        if (existingLike != null) {
            // 已点赞，幂等返回
            log.debug("用户已点赞过该笔记，幂等返回: userId={}, noteId={}", userId, noteId);
            return;
        }

        // 插入点赞记录
        NoteLike noteLike = new NoteLike();
        noteLike.setUserId(userId);
        noteLike.setNoteId(noteId);
        noteLike.setCreateTime(LocalDateTime.now());

        try {
            noteLikeMapper.insert(noteLike);
        } catch (DuplicateKeyException e) {
            // 唯一索引冲突，说明已点赞，幂等返回
            log.debug("点赞记录已存在（唯一索引冲突），幂等返回: userId={}, noteId={}", userId, noteId);
            return;
        }

        // 点赞成功，增加计数
        noteMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<FoodNote>()
                .eq(FoodNote::getId, noteId)
                .setSql("like_count = COALESCE(like_count, 0) + 1"));

        // 通知作者
        if (notificationService != null && !note.getAuthorId().equals(userId)) {
            notificationService.sendNotification(note.getAuthorId(), 2, "💕 收到点赞",
                "你的笔记「" + note.getTitle() + "」收到了一个赞", noteId, "note");
        }

        log.info("点赞成功: userId={}, noteId={}", userId, noteId);
    }

    @Override
    @Transactional
    public void unlikeNote(Long userId, Long noteId) {
        FoodNote note = noteMapper.selectById(noteId);
        if (note == null) {
            throw BusinessException.NOTE_NOT_FOUND;
        }

        // 查找点赞记录
        NoteLike existingLike = noteLikeMapper.selectOne(
            new LambdaQueryWrapper<NoteLike>()
                .eq(NoteLike::getUserId, userId)
                .eq(NoteLike::getNoteId, noteId)
        );

        if (existingLike == null) {
            // 未点赞，幂等返回
            log.debug("用户未点赞过该笔记，幂等返回: userId={}, noteId={}", userId, noteId);
            return;
        }

        // 删除点赞记录
        int deleted = noteLikeMapper.deleteById(existingLike.getId());
        if (deleted > 0) {
            // 取消点赞成功，减少计数
            noteMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<FoodNote>()
                    .eq(FoodNote::getId, noteId)
                    .gt(FoodNote::getLikeCount, 0)
                    .setSql("like_count = like_count - 1"));
            log.info("取消点赞成功: userId={}, noteId={}", userId, noteId);
        }
    }

    @Override
    public void commentNote(Long userId, Long noteId, String content) {
        // 简化处理：评论功能后续完善
        log.info("评论笔记: userId={}, noteId={}, content={}", userId, noteId, content);

        FoodNote note = noteMapper.selectById(noteId);
        if (note != null) {
            // 使用原子更新避免竞态条件
            noteMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<FoodNote>()
                    .eq(FoodNote::getId, noteId)
                    .setSql("comment_count = COALESCE(comment_count, 0) + 1"));

            if (notificationService != null && !note.getAuthorId().equals(userId)) {
                notificationService.sendNotification(note.getAuthorId(), 2, "💬 新评论",
                    "有人评论了你的笔记：「" + note.getTitle() + "」", noteId, "note");
            }
        }
    }

    @Override
    public void incrementViewCount(Long noteId) {
        // 使用原子更新避免竞态条件
        noteMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<FoodNote>()
                .eq(FoodNote::getId, noteId)
                .setSql("view_count = COALESCE(view_count, 0) + 1"));
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private Long getPartnerId(User user) {
        if (user.getCoupleId() == null) {
            return null;
        }
        List<User> users = userMapper.selectList(
            new LambdaQueryWrapper<User>()
                .eq(User::getCoupleId, user.getCoupleId())
                .ne(User::getId, user.getId())
        );
        return users.isEmpty() ? null : users.get(0).getId();
    }

    private FoodNoteDTO buildNoteDTO(FoodNote note) {
        return buildNoteDTOWithCache(note, null, null);
    }

    /**
     * 构建DTO（使用缓存的用户和纪念日数据，避免N+1查询）
     */
    private FoodNoteDTO buildNoteDTOWithCache(FoodNote note, Map<Long, User> userMap, Map<Long, Anniversary> anniversaryMap) {
        FoodNoteDTO dto = new FoodNoteDTO();
        dto.setId(note.getId());
        dto.setCoupleId(note.getCoupleId());
        dto.setAuthorId(note.getAuthorId());
        dto.setTitle(note.getTitle());
        dto.setContent(note.getContent());
        dto.setLocation(note.getLocation());
        dto.setLatitude(note.getLatitude() != null ? note.getLatitude().doubleValue() : null);
        dto.setLongitude(note.getLongitude() != null ? note.getLongitude().doubleValue() : null);
        dto.setIsAnniversaryLinked(note.getIsAnniversaryLinked() != null && note.getIsAnniversaryLinked() == 1);
        dto.setAnniversaryId(note.getAnniversaryId());
        dto.setViewCount(note.getViewCount());
        dto.setLikeCount(note.getLikeCount());
        dto.setCommentCount(note.getCommentCount());
        dto.setPhotoUrls(note.getPhotoUrls() != null ? JSONUtil.toList(note.getPhotoUrls(), String.class) : new ArrayList<>());
        dto.setCreateTime(note.getCreateTime() != null ? note.getCreateTime().toString() : null);

        // 获取作者信息（使用缓存或单独查询）
        if (note.getAuthorId() != null) {
            User author = userMap != null ? userMap.get(note.getAuthorId()) : userMapper.selectById(note.getAuthorId());
            if (author != null) {
                dto.setAuthorName(author.getNickName());
                dto.setAuthorAvatar(author.getAvatarUrl());
            }
        }

        // 获取纪念日名称（使用缓存或单独查询）
        if (note.getAnniversaryId() != null) {
            Anniversary anniversary = anniversaryMap != null ? anniversaryMap.get(note.getAnniversaryId()) : anniversaryMapper.selectById(note.getAnniversaryId());
            if (anniversary != null) {
                dto.setAnniversaryName(anniversary.getName());
            }
        }

        return dto;
    }
}