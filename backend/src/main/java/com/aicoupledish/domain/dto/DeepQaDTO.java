package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 深度问答DTO
 */
@Data
public class DeepQaDTO {

    private Long id;

    /**
     * 周数
     */
    private Integer weekNumber;

    /**
     * 问题内容
     */
    private String questionText;

    /**
     * 问题类型
     */
    private String questionType;

    /**
     * 选项列表
     */
    private List<String> options;

    /**
     * 分类
     */
    private String category;

    /**
     * 分类名称
     */
    private String categoryName;

    /**
     * 我的答案
     */
    private AnswerInfo myAnswer;

    /**
     * 对方的答案
     */
    private AnswerInfo partnerAnswer;

    /**
     * 是否已揭晓
     */
    private Boolean isRevealed;

    /**
     * 当前进度
     */
    private ProgressInfo progress;

    /**
     * 答案信息
     */
    @Data
    public static class AnswerInfo {
        private Long id;
        private Long userId;
        private String userName;
        private String userAvatar;
        private String answerText;
        private LocalDateTime createTime;
    }

    /**
     * 进度信息
     */
    @Data
    public static class ProgressInfo {
        private Integer currentWeek;
        private Integer currentQuestion;
        private Integer totalCompleted;
        private Integer totalQuestions;
    }

    /**
     * 提交答案请求
     */
    @Data
    public static class SubmitAnswerReq {
        private Long questionId;
        private String answerText;
    }
}
