-- 笔记点赞关系表（幂等化点赞）
CREATE TABLE IF NOT EXISTS `t_note_like` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `note_id` BIGINT NOT NULL COMMENT '笔记ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_note_user` (`note_id`, `user_id`) COMMENT '同一用户对同一笔记只能点赞一次',
    KEY `idx_user_id` (`user_id`) COMMENT '用户ID索引',
    KEY `idx_note_id` (`note_id`) COMMENT '笔记ID索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='笔记点赞关系表';
