package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.GreetingStreak;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 问候连续打卡Mapper
 */
@Mapper
public interface GreetingStreakMapper extends BaseMapper<GreetingStreak> {
}
