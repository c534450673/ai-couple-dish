package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.Wish;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

import java.time.LocalDateTime;

/**
 * 心愿单Mapper
 */
@Mapper
public interface WishMapper extends BaseMapper<Wish> {

    /**
     * 原子更新查看者信息（仅当viewer_id为空时更新）
     * @return 影响行数，1表示更新成功，0表示已被其他用户查看
     */
    @Update("UPDATE wish SET viewer_id = #{viewerId}, view_time = #{viewTime} WHERE id = #{wishId} AND viewer_id IS NULL AND is_deleted = 0")
    int updateViewerAtomic(@Param("wishId") Long wishId, @Param("viewerId") Long viewerId, @Param("viewTime") LocalDateTime viewTime);
}