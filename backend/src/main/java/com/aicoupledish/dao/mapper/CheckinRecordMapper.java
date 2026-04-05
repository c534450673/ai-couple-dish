package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.CheckinRecord;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 打卡记录Mapper
 */
@Mapper
public interface CheckinRecordMapper extends BaseMapper<CheckinRecord> {
}
