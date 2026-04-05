package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.Wish;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 心愿单Mapper
 */
@Mapper
public interface WishMapper extends BaseMapper<Wish> {
}