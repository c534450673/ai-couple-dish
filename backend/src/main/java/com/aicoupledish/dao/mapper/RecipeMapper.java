package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.Recipe;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Update;

/**
 * 菜谱Mapper
 */
@Mapper
public interface RecipeMapper extends BaseMapper<Recipe> {

    /**
     * 原子增加点赞数
     */
    @Update("UPDATE t_recipe SET like_count = like_count + 1 WHERE id = #{recipeId} AND is_deleted = 0")
    int incrementLikeCount(Long recipeId);

    /**
     * 原子减少点赞数
     */
    @Update("UPDATE t_recipe SET like_count = GREATEST(0, like_count - 1) WHERE id = #{recipeId} AND is_deleted = 0")
    int decrementLikeCount(Long recipeId);

    /**
     * 原子增加收藏数
     */
    @Update("UPDATE t_recipe SET collect_count = collect_count + 1 WHERE id = #{recipeId} AND is_deleted = 0")
    int incrementCollectCount(Long recipeId);

    /**
     * 原子减少收藏数
     */
    @Update("UPDATE t_recipe SET collect_count = GREATEST(0, collect_count - 1) WHERE id = #{recipeId} AND is_deleted = 0")
    int decrementCollectCount(Long recipeId);
}
