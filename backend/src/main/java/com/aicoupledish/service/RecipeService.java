package com.aicoupledish.service;

import com.aicoupledish.domain.dto.RecipeDTO;
import com.aicoupledish.domain.req.CreateRecipeReq;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import java.util.List;

/**
 * 菜谱服务
 */
public interface RecipeService {

    /**
     * 创建菜谱
     *
     * @param userId 用户ID
     * @param req    创建请求
     * @return 菜谱ID
     */
    Long createRecipe(Long userId, CreateRecipeReq req);

    /**
     * 更新菜谱
     *
     * @param userId   用户ID
     * @param recipeId 菜谱ID
     * @param req      更新请求
     */
    void updateRecipe(Long userId, Long recipeId, CreateRecipeReq req);

    /**
     * 删除菜谱
     *
     * @param userId   用户ID
     * @param recipeId 菜谱ID
     */
    void deleteRecipe(Long userId, Long recipeId);

    /**
     * 发布菜谱
     *
     * @param userId   用户ID
     * @param recipeId 菜谱ID
     */
    void publishRecipe(Long userId, Long recipeId);

    /**
     * 获取菜谱详情
     *
     * @param userId   用户ID（可选）
     * @param recipeId 菜谱ID
     * @return 菜谱详情
     */
    RecipeDTO getRecipeDetail(Long userId, Long recipeId);

    /**
     * 获取我的菜谱列表
     *
     * @param userId   用户ID
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 菜谱分页
     */
    Page<RecipeDTO> getMyRecipes(Long userId, Integer pageNum, Integer pageSize);

    /**
     * 获取情侣的菜谱列表
     *
     * @param userId   用户ID
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 菜谱分页
     */
    Page<RecipeDTO> getCoupleRecipes(Long userId, Integer pageNum, Integer pageSize);

    /**
     * 获取推荐菜谱列表
     *
     * @param userId   用户ID
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 菜谱分页
     */
    Page<RecipeDTO> getRecommendedRecipes(Long userId, Integer pageNum, Integer pageSize);

    /**
     * 点赞菜谱
     *
     * @param userId   用户ID
     * @param recipeId 菜谱ID
     */
    void likeRecipe(Long userId, Long recipeId);

    /**
     * 取消点赞
     *
     * @param userId   用户ID
     * @param recipeId 菜谱ID
     */
    void unlikeRecipe(Long userId, Long recipeId);

    /**
     * 收藏菜谱
     *
     * @param userId   用户ID
     * @param recipeId 菜谱ID
     */
    void collectRecipe(Long userId, Long recipeId);

    /**
     * 取消收藏
     *
     * @param userId   用户ID
     * @param recipeId 菜谱ID
     */
    void uncollectRecipe(Long userId, Long recipeId);

    /**
     * 获取收藏的菜谱列表
     *
     * @param userId   用户ID
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 菜谱分页
     */
    Page<RecipeDTO> getCollectedRecipes(Long userId, Integer pageNum, Integer pageSize);

    /**
     * 搜索菜谱
     *
     * @param userId   用户ID
     * @param keyword  关键词
     * @param pageNum  页码
     * @param pageSize 每页大小
     * @return 菜谱分页
     */
    Page<RecipeDTO> searchRecipes(Long userId, String keyword, Integer pageNum, Integer pageSize);
}
