package com.aicoupledish.domain.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 菜谱DTO
 */
@Data
public class RecipeDTO {

    /**
     * 菜谱ID
     */
    private Long id;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 用户名称
     */
    private String userName;

    /**
     * 用户头像
     */
    private String userAvatar;

    /**
     * 菜谱标题
     */
    private String title;

    /**
     * 封面URL
     */
    private String coverUrl;

    /**
     * 菜谱描述
     */
    private String description;

    /**
     * 食材列表
     */
    private List<IngredientDTO> ingredients;

    /**
     * 制作步骤
     */
    private List<StepDTO> steps;

    /**
     * 难度
     */
    private String difficulty;

    /**
     * 难度描述
     */
    private String difficultyDesc;

    /**
     * 烹饪时间（分钟）
     */
    private Integer cookingTime;

    /**
     * 份量
     */
    private Integer servings;

    /**
     * 状态
     */
    private Integer status;

    /**
     * 点赞数
     */
    private Integer likeCount;

    /**
     * 收藏数
     */
    private Integer collectCount;

    /**
     * 是否已点赞
     */
    private Boolean liked;

    /**
     * 是否已收藏
     */
    private Boolean collected;

    /**
     * 收藏时间
     */
    private String collectTime;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 食材DTO
     */
    @Data
    public static class IngredientDTO {
        private String name;
        private String amount;
    }

    /**
     * 步骤DTO
     */
    @Data
    public static class StepDTO {
        private Integer stepNo;
        private String content;
        private String imageUrl;
    }
}
