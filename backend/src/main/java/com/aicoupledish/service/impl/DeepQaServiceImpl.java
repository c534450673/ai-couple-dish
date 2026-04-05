package com.aicoupledish.service.impl;

import com.aicoupledish.common.enums.BusinessException;
import com.aicoupledish.dao.mapper.*;
import com.aicoupledish.dao.model.*;
import com.aicoupledish.domain.dto.DeepQaDTO;
import com.aicoupledish.service.DeepQaService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 情侣深度问答服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeepQaServiceImpl implements DeepQaService {

    private final DeepQuestionMapper deepQuestionMapper;
    private final CoupleQaProgressMapper coupleQaProgressMapper;
    private final DeepQaAnswerMapper deepQaAnswerMapper;
    private final UserMapper userMapper;
    private final CoupleMapper coupleMapper;

    @Override
    public DeepQaDTO getCurrentQuestion(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleQaProgress progress = getOrCreateProgress(user.getCoupleId());
        DeepQuestion question = getQuestionByProgress(progress);

        if (question == null) {
            return null;
        }

        return buildDTO(question, user);
    }

    @Override
    public List<DeepQaDTO> getWeekQuestions(Long userId, Integer weekNumber) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        List<DeepQuestion> questions = deepQuestionMapper.selectList(
            new LambdaQueryWrapper<DeepQuestion>()
                    .eq(DeepQuestion::getWeekNumber, weekNumber)
                    .eq(DeepQuestion::getIsActive, 1)
                    .orderByAsc(DeepQuestion::getSortOrder)
        );

        return questions.stream().map(q -> buildDTO(q, user)).collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void submitAnswer(Long userId, DeepQaDTO.SubmitAnswerReq req) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 检查是否已回答
        Long existCount = deepQaAnswerMapper.selectCount(
            new LambdaQueryWrapper<DeepQaAnswer>()
                    .eq(DeepQaAnswer::getQuestionId, req.getQuestionId())
                    .eq(DeepQaAnswer::getUserId, userId)
        );

        if (existCount != null && existCount > 0) {
            throw new IllegalStateException("该问题已回答过");
        }

        // 保存答案
        DeepQaAnswer answer = new DeepQaAnswer();
        answer.setCoupleId(user.getCoupleId());
        answer.setQuestionId(req.getQuestionId());
        answer.setUserId(userId);
        answer.setAnswerText(req.getAnswerText());
        answer.setIsRevealed(0);
        deepQaAnswerMapper.insert(answer);

        // 更新进度
        updateProgress(user.getCoupleId());

        log.info("提交深度问答答案: userId={}, questionId={}", userId, req.getQuestionId());
    }

    @Override
    @Transactional
    public DeepQaDTO revealAnswer(Long userId, Long questionId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 检查双方是否都已回答
        Couple couple = coupleMapper.selectById(user.getCoupleId());
        Long partnerId = couple.getUser1Id().equals(userId) ? couple.getUser2Id() : couple.getUser1Id();

        Long myAnswer = deepQaAnswerMapper.selectCount(
            new LambdaQueryWrapper<DeepQaAnswer>()
                    .eq(DeepQaAnswer::getQuestionId, questionId)
                    .eq(DeepQaAnswer::getUserId, userId)
        );

        Long partnerAnswer = deepQaAnswerMapper.selectCount(
            new LambdaQueryWrapper<DeepQaAnswer>()
                    .eq(DeepQaAnswer::getQuestionId, questionId)
                    .eq(DeepQaAnswer::getUserId, partnerId)
        );

        if (myAnswer == null || myAnswer == 0 || partnerAnswer == null || partnerAnswer == 0) {
            throw new IllegalStateException("双方都回答后才能揭晓");
        }

        // 揭晓答案
        List<DeepQaAnswer> answers = deepQaAnswerMapper.selectList(
            new LambdaQueryWrapper<DeepQaAnswer>()
                    .eq(DeepQaAnswer::getQuestionId, questionId)
                    .eq(DeepQaAnswer::getCoupleId, user.getCoupleId())
        );

        for (DeepQaAnswer answer : answers) {
            if (answer.getIsRevealed() == 0) {
                answer.setIsRevealed(1);
                answer.setRevealTime(LocalDateTime.now());
                deepQaAnswerMapper.updateById(answer);
            }
        }

        DeepQuestion question = deepQuestionMapper.selectById(questionId);
        return buildDTO(question, user);
    }

    @Override
    public DeepQaDTO.ProgressInfo getProgress(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleQaProgress progress = getOrCreateProgress(user.getCoupleId());
        Long totalQuestions = deepQuestionMapper.selectCount(
            new LambdaQueryWrapper<DeepQuestion>().eq(DeepQuestion::getIsActive, 1)
        );

        DeepQaDTO.ProgressInfo info = new DeepQaDTO.ProgressInfo();
        info.setCurrentWeek(progress.getCurrentWeek());
        info.setCurrentQuestion(progress.getCurrentQuestion());
        info.setTotalCompleted(progress.getTotalCompleted());
        info.setTotalQuestions(totalQuestions != null ? totalQuestions.intValue() : 0);

        return info;
    }

    @Override
    public List<DeepQaDTO> getHistoryAnswers(Long userId, Integer limit) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        // 获取已揭晓的答案
        List<DeepQaAnswer> answers = deepQaAnswerMapper.selectList(
            new LambdaQueryWrapper<DeepQaAnswer>()
                    .eq(DeepQaAnswer::getCoupleId, user.getCoupleId())
                    .eq(DeepQaAnswer::getIsRevealed, 1)
                    .orderByDesc(DeepQaAnswer::getRevealTime)
                    .last("LIMIT " + (limit != null ? limit : 20))
        );

        return answers.stream()
                .map(a -> {
                    DeepQuestion question = deepQuestionMapper.selectById(a.getQuestionId());
                    return buildDTO(question, user);
                })
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void skipQuestion(Long userId) {
        User user = getUserById(userId);
        if (user.getCoupleId() == null) {
            throw BusinessException.COUPLE_NOT_BIND;
        }

        CoupleQaProgress progress = getOrCreateProgress(user.getCoupleId());
        progress.setCurrentQuestion(progress.getCurrentQuestion() + 1);
        coupleQaProgressMapper.updateById(progress);

        log.info("跳过问题: userId={}", userId);
    }

    @Override
    @Transactional
    public void initQuestionBank() {
        // 检查是否已有题目
        Long count = deepQuestionMapper.selectCount(new LambdaQueryWrapper<>());
        if (count != null && count > 0) {
            return;
        }

        // 初始化题目
        List<String> questions = List.of(
                "你最喜欢的旅行目的地是哪里？为什么？",
                "你觉得什么是幸福？",
                "如果你可以拥有一种超能力，你会选择什么？",
                "你小时候的梦想是什么？",
                "你最喜欢的家庭传统是什么？",
                "你认为两个人在一起最重要的是什么？",
                "你最难忘的一次约会是什么样的？",
                "你对未来有什么规划？",
                "你最喜欢对方哪一点？",
                "你希望怎样度过退休生活？"
        );

        int week = 1;
        int order = 1;
        for (String questionText : questions) {
            DeepQuestion question = new DeepQuestion();
            question.setWeekNumber(week);
            question.setQuestionText(questionText);
            question.setQuestionType("open");
            question.setCategory("relationship");
            question.setSortOrder(order++);
            question.setIsActive(1);
            deepQuestionMapper.insert(question);

            // 每7道题换一周
            if (order > 7) {
                week++;
                order = 1;
            }
        }

        log.info("初始化题目库完成，共{}道题", questions.size());
    }

    private CoupleQaProgress getOrCreateProgress(Long coupleId) {
        CoupleQaProgress progress = coupleQaProgressMapper.selectOne(
            new LambdaQueryWrapper<CoupleQaProgress>()
                    .eq(CoupleQaProgress::getCoupleId, coupleId)
        );

        if (progress == null) {
            progress = new CoupleQaProgress();
            progress.setCoupleId(coupleId);
            progress.setCurrentWeek(1);
            progress.setCurrentQuestion(1);
            progress.setTotalCompleted(0);
            coupleQaProgressMapper.insert(progress);
        }

        return progress;
    }

    private DeepQuestion getQuestionByProgress(CoupleQaProgress progress) {
        return deepQuestionMapper.selectOne(
            new LambdaQueryWrapper<DeepQuestion>()
                    .eq(DeepQuestion::getWeekNumber, progress.getCurrentWeek())
                    .eq(DeepQuestion::getIsActive, 1)
                    .orderByAsc(DeepQuestion::getSortOrder)
                    .last("LIMIT 1 OFFSET " + (progress.getCurrentQuestion() - 1))
        );
    }

    private void updateProgress(Long coupleId) {
        CoupleQaProgress progress = getOrCreateProgress(coupleId);

        // 使用乐观锁更新进度，避免竞态条件
        int currentQuestion = progress.getCurrentQuestion();
        int currentWeek = progress.getCurrentWeek();

        // 检查是否需要进入下一周
        Long weekQuestions = deepQuestionMapper.selectCount(
            new LambdaQueryWrapper<DeepQuestion>()
                    .eq(DeepQuestion::getWeekNumber, currentWeek)
                    .eq(DeepQuestion::getIsActive, 1)
        );

        int newQuestion = currentQuestion + 1;
        int newWeek = currentWeek;

        if (newQuestion > (weekQuestions != null ? weekQuestions.intValue() : 7)) {
            newWeek = currentWeek + 1;
            newQuestion = 1;
        }

        // 原子更新
        int updated = coupleQaProgressMapper.update(null,
            new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<CoupleQaProgress>()
                .eq(CoupleQaProgress::getId, progress.getId())
                .eq(CoupleQaProgress::getCurrentQuestion, currentQuestion)  // 乐观锁
                .set(CoupleQaProgress::getTotalCompleted, progress.getTotalCompleted() + 1)
                .set(CoupleQaProgress::getCurrentQuestion, newQuestion)
                .set(CoupleQaProgress::getCurrentWeek, newWeek)
        );

        if (updated == 0) {
            // 更新失败，说明有并发修改，重新获取并更新
            log.warn("进度更新冲突，重试: coupleId={}", coupleId);
            CoupleQaProgress retryProgress = getOrCreateProgress(coupleId);
            // 不再递归调用，直接更新
            coupleQaProgressMapper.update(null,
                new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<CoupleQaProgress>()
                    .eq(CoupleQaProgress::getId, retryProgress.getId())
                    .setSql("total_completed = total_completed + 1")
                    .setSql("current_question = current_question + 1")
            );
        }
    }

    private User getUserById(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw BusinessException.USER_NOT_FOUND;
        }
        return user;
    }

    private DeepQaDTO buildDTO(DeepQuestion question, User user) {
        DeepQaDTO dto = new DeepQaDTO();
        dto.setId(question.getId());
        dto.setWeekNumber(question.getWeekNumber());
        dto.setQuestionText(question.getQuestionText());
        dto.setQuestionType(question.getQuestionType());
        dto.setCategory(question.getCategory());
        dto.setCategoryName(getCategoryName(question.getCategory()));

        // 获取答案
        DeepQaAnswer myAnswer = deepQaAnswerMapper.selectOne(
            new LambdaQueryWrapper<DeepQaAnswer>()
                    .eq(DeepQaAnswer::getQuestionId, question.getId())
                    .eq(DeepQaAnswer::getUserId, user.getId())
        );

        if (myAnswer != null) {
            DeepQaDTO.AnswerInfo answerInfo = new DeepQaDTO.AnswerInfo();
            answerInfo.setId(myAnswer.getId());
            answerInfo.setUserId(user.getId());
            answerInfo.setUserName(user.getNickName());
            answerInfo.setUserAvatar(user.getAvatarUrl());
            answerInfo.setAnswerText(myAnswer.getAnswerText());
            answerInfo.setCreateTime(myAnswer.getCreateTime());
            dto.setMyAnswer(answerInfo);
            dto.setIsRevealed(myAnswer.getIsRevealed() == 1);
        }

        // 获取伴侣答案
        if (user.getCoupleId() != null) {
            Couple couple = coupleMapper.selectById(user.getCoupleId());
            if (couple != null) {
                Long partnerId = couple.getUser1Id().equals(user.getId()) ? couple.getUser2Id() : couple.getUser1Id();
                DeepQaAnswer partnerAnswer = deepQaAnswerMapper.selectOne(
                    new LambdaQueryWrapper<DeepQaAnswer>()
                            .eq(DeepQaAnswer::getQuestionId, question.getId())
                            .eq(DeepQaAnswer::getUserId, partnerId)
                );

                if (partnerAnswer != null && partnerAnswer.getIsRevealed() == 1) {
                    User partner = userMapper.selectById(partnerId);
                    DeepQaDTO.AnswerInfo answerInfo = new DeepQaDTO.AnswerInfo();
                    answerInfo.setId(partnerAnswer.getId());
                    answerInfo.setUserId(partnerId);
                    answerInfo.setUserName(partner != null ? partner.getNickName() : "");
                    answerInfo.setUserAvatar(partner != null ? partner.getAvatarUrl() : "");
                    answerInfo.setAnswerText(partnerAnswer.getAnswerText());
                    answerInfo.setCreateTime(partnerAnswer.getCreateTime());
                    dto.setPartnerAnswer(answerInfo);
                }
            }
        }

        return dto;
    }

    private String getCategoryName(String category) {
        switch (category) {
            case "relationship": return "感情";
            case "future": return "未来";
            case "values": return "价值观";
            case "dreams": return "梦想";
            default: return category;
        }
    }
}
