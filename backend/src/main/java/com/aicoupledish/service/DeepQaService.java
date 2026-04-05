package com.aicoupledish.service;

import com.aicoupledish.domain.dto.DeepQaDTO;

import java.util.List;

/**
 * 情侣深度问答服务接口
 */
public interface DeepQaService {

    /**
     * 获取当前问题
     */
    DeepQaDTO getCurrentQuestion(Long userId);

    /**
     * 获取指定周的问题列表
     */
    List<DeepQaDTO> getWeekQuestions(Long userId, Integer weekNumber);

    /**
     * 提交答案
     */
    void submitAnswer(Long userId, DeepQaDTO.SubmitAnswerReq req);

    /**
     * 揭晓答案
     */
    DeepQaDTO revealAnswer(Long userId, Long questionId);

    /**
     * 获取进度
     */
    DeepQaDTO.ProgressInfo getProgress(Long userId);

    /**
     * 获取历史问答记录
     */
    List<DeepQaDTO> getHistoryAnswers(Long userId, Integer limit);

    /**
     * 跳过当前问题
     */
    void skipQuestion(Long userId);

    /**
     * 初始化题目库
     */
    void initQuestionBank();
}
