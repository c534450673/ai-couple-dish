package com.aicoupledish.dao.mapper;

import com.aicoupledish.dao.model.GreetingStreak;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDate;

/**
 * 问候连续打卡Mapper
 */
@Mapper
public interface GreetingStreakMapper extends BaseMapper<GreetingStreak> {

    @Insert("""
        INSERT INTO t_greeting_streak (
            couple_id, streak_type, streak_days, max_streak_days, last_date
        ) VALUES (
            #{coupleId}, #{streakType}, 1, 1, #{businessDate}
        )
        ON DUPLICATE KEY UPDATE
            streak_days = CASE
                WHEN last_date = VALUES(last_date) THEN streak_days
                WHEN last_date = DATE_SUB(VALUES(last_date), INTERVAL 1 DAY)
                    THEN streak_days + 1
                WHEN last_date > VALUES(last_date) THEN streak_days
                ELSE 1
            END,
            max_streak_days = GREATEST(max_streak_days, streak_days),
            last_date = CASE
                WHEN last_date IS NULL OR last_date < VALUES(last_date)
                    THEN VALUES(last_date)
                ELSE last_date
            END,
            update_time = CURRENT_TIMESTAMP
        """)
    int upsert(
        @Param("coupleId") Long coupleId,
        @Param("streakType") Integer streakType,
        @Param("businessDate") LocalDate businessDate
    );
}
