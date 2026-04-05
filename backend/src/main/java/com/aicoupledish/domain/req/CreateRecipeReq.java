package com.aicoupledish.domain.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;
import java.util.List;

/**
 * 创建菜谱请求
 */
@Data
public class CreateRecipeReq {

    /**
     * 菜谱标题
     */
    @NotBlank(message = "菜谱标题不能为空")
    @Size(max = 256, message = "菜谱标题最长256个字符")
    private String title;

    /**
     * 封面URL
     */
    private String coverUrl;

    /**
     * 菜谱描述
     */
    @Size(max = 2000, message = "菜谱描述最长2000个字符")
    private String description;

    /**
     * 食材列表
     */
    private List<IngredientReq> ingredients;

    /**
     * 制作步骤
     */
    private List<StepReq> steps;

    /**
     * 难度
     */
    private String difficulty;

    /**
     * 烹饪时间（分钟）
     */
    private Integer cookingTime;

    /**
     * 份量
     */
    private Integer servings;

    /**
     * 是否发布
     */
    private Boolean publish;

    /**
     * 食材请求
     */
    @Data
    public static class IngredientReq {
        private String name;
        private String amount;
    }

    /**
     * 步骤请求
     */
    @Data
    public static class StepReq {
        private String content;
        private String imageUrl;
    }
}
