package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.MoodRecord;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 心情记录Mapper
 */
@Mapper
public interface MoodRecordMapper extends BaseMapper<MoodRecord> {
}
