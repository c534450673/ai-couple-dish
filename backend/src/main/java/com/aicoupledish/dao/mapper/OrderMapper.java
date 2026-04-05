package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.Order;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 订单Mapper
 */
@Mapper
public interface OrderMapper extends BaseMapper<Order> {
}
