package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 随机甜蜜炸弹DTO
 */
@Data
public class SweetBombDTO {

    private Long id;

    /**
     * 类型: memory/data/festival/question
     */
    private String bombType;

    /**
     * 类型名称
     */
    private String bombTypeName;

    /**
     * 炸弹内容
     */
    private BombContent content;

    /**
     * 发送时间
     */
    private LocalDateTime sentTime;

    /**
     * 是否已读
     */
    private Boolean isRead;

    /**
     * 是否已回答
     */
    private Boolean isAnswered;

    /**
     * 回答内容
     */
    private String answerContent;

    /**
     * 回答时间
     */
    private LocalDateTime answerTime;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 炸弹内容
     */
    @Data
    public static class BombContent {
        /**
         * 标题
         */
        private String title;

        /**
         * 描述
         */
        private String description;

        /**
         * 问题（问答类型）
         */
        private String question;

        /**
         * 选项（选择类型）
         */
        private List<String> options;

        /**
         * 回忆数据
         */
        private MemoryData memoryData;

        /**
         * 统计数据
         */
        private Map<String, Object> statsData;

        /**
         * 额外信息
         */
        private Map<String, Object> extraInfo;
    }

    /**
     * 回忆数据
     */
    @Data
    public static class MemoryData {
        private String memoryType;
        private String memoryContent;
        private LocalDateTime memoryTime;
        private String relatedUrl;
    }

    /**
     * 生成炸弹请求
     */
    @Data
    public static class GenerateReq {
        /**
         * 炸弹类型
         */
        private String bombType;
    }

    /**
     * 回答炸弹请求
     */
    @Data
    public static class AnswerReq {
        /**
         * 答案内容
         */
        private String answerContent;
    }
}
