package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.Cart;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 购物车Mapper
 */
@Mapper
public interface CartMapper extends BaseMapper<Cart> {
}
