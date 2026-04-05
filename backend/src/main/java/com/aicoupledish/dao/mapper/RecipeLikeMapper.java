package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.RecipeLike;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 菜谱点赞Mapper
 */
@Mapper
public interface RecipeLikeMapper extends BaseMapper<RecipeLike> {
}
