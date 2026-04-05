package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.FoodNote;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 美食笔记Mapper
 */
@Mapper
public interface FoodNoteMapper extends BaseMapper<FoodNote> {
}