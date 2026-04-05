-- 性能优化索引迁移脚本
-- 执行前请先在测试环境验证
-- 执行时间建议：数据库低峰期

-- 1. 纪念日表复合索引（按情侣查询未删除记录）
ALTER TABLE t_anniversary ADD INDEX idx_couple_deleted (couple_id, is_deleted);

-- 2. 菜单表复合索引（按情侣查询未删除记录并按状态筛选）
ALTER TABLE t_couple_menu ADD INDEX idx_couple_deleted_status (couple_id, is_deleted, status);

-- 3. 美食笔记表复合索引（按情侣查询未删除记录）
ALTER TABLE t_food_note ADD INDEX idx_couple_deleted (couple_id, is_deleted);

-- 4. 心愿表复合索引（按情侣查询未完成心愿）
ALTER TABLE t_wish ADD INDEX idx_couple_status (couple_id, status);

-- 5. 时光胶囊表索引
ALTER TABLE t_time_capsule ADD INDEX idx_couple_open_time (couple_id, open_time);

-- 6. 心动时刻表索引
ALTER TABLE t_heart_moment ADD INDEX idx_couple_create_time (couple_id, create_time);

-- 7. 每日问候表索引
ALTER TABLE t_daily_greeting ADD INDEX idx_couple_date_type (couple_id, greeting_date, greeting_type);

-- 8. 情侣树表索引
ALTER TABLE t_couple_tree ADD INDEX idx_couple_level (couple_id, level);

-- 9. 用户手机号索引（如不存在）
-- ALTER TABLE t_user ADD INDEX idx_phone (phone);

-- 验证索引创建
-- SHOW INDEX FROM t_anniversary WHERE Key_name = 'idx_couple_deleted';
-- SHOW INDEX FROM t_couple_menu WHERE Key_name = 'idx_couple_deleted_status';
-- SHOW INDEX FROM t_food_note WHERE Key_name = 'idx_couple_deleted';
