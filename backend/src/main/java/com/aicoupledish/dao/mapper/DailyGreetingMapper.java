package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.DailyGreeting;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 每日问候Mapper
 */
@Mapper
public interface DailyGreetingMapper extends BaseMapper<DailyGreeting> {
}
