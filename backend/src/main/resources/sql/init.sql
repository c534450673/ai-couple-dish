-- 情侣私密菜单 V1.0 数据库初始化脚本

-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai_couple_dish DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ai_couple_dish;

-- ----------------------------
-- 1. 用户表
-- ----------------------------
DROP TABLE IF EXISTS t_user;
CREATE TABLE t_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    openid VARCHAR(64) NOT NULL COMMENT '微信openid',
    nick_name VARCHAR(64) DEFAULT NULL COMMENT '昵称',
    avatar_url VARCHAR(512) DEFAULT NULL COMMENT '头像URL',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    gender TINYINT DEFAULT 0 COMMENT '性别：0-未知 1-男 2-女',
    couple_id BIGINT DEFAULT NULL COMMENT '情侣ID',
    love_start_date DATETIME DEFAULT NULL COMMENT '恋爱开始日期',
    taste_preferences TEXT COMMENT '口味偏好（JSON）',
    food_restrictions TEXT COMMENT '忌口（JSON）',
    member_level TINYINT DEFAULT 0 COMMENT '会员等级：0-免费 1-黄金 2-铂金',
    status TINYINT DEFAULT 0 COMMENT '状态：0-正常 1-禁用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除：0-未删除 1-已删除',
    INDEX idx_openid (openid),
    INDEX idx_couple_id (couple_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ----------------------------
-- 2. 情侣关系表
-- ----------------------------
DROP TABLE IF EXISTS t_couple;
CREATE TABLE t_couple (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_code VARCHAR(16) NOT NULL COMMENT '情侣码',
    user_1_id BIGINT NOT NULL COMMENT '用户1ID（发起方）',
    user_2_id BIGINT NOT NULL COMMENT '用户2ID（确认方）',
    start_date DATE DEFAULT NULL COMMENT '恋爱开始日期',
    love_days INT DEFAULT 0 COMMENT '恋爱天数',
    couple_nickname VARCHAR(128) DEFAULT NULL COMMENT '情侣昵称',
    status TINYINT DEFAULT 0 COMMENT '状态：0-待确认 1-已绑定 2-已解除 3-申请解绑中',
    unbind_applicant_id BIGINT DEFAULT NULL COMMENT '解绑申请者ID',
    unbind_apply_time DATETIME DEFAULT NULL COMMENT '解绑申请时间',
    avatar_frame VARCHAR(64) DEFAULT NULL COMMENT '头像框样式',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_code (couple_code),
    INDEX idx_user_1 (user_1_id),
    INDEX idx_user_2 (user_2_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情侣关系表';

-- ----------------------------
-- 3. 私密菜单表
-- ----------------------------
DROP TABLE IF EXISTS t_couple_menu;
CREATE TABLE t_couple_menu (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    restaurant_name VARCHAR(256) NOT NULL COMMENT '餐厅名称',
    dish_name VARCHAR(256) DEFAULT NULL COMMENT '菜品名称',
    dish_category VARCHAR(64) DEFAULT NULL COMMENT '菜品分类/标签',
    price DECIMAL(10,2) DEFAULT NULL COMMENT '人均价格',
    location VARCHAR(512) DEFAULT NULL COMMENT '位置信息',
    latitude DECIMAL(10,8) DEFAULT NULL COMMENT '纬度',
    longitude DECIMAL(11,8) DEFAULT NULL COMMENT '经度',
    note TEXT COMMENT '私密笔记',
    rating TINYINT DEFAULT NULL COMMENT '评分1-5星',
    eater_ids VARCHAR(512) DEFAULT NULL COMMENT '用餐人IDs（JSON数组）',
    eaten_date DATE DEFAULT NULL COMMENT '用餐日期',
    status TINYINT DEFAULT 0 COMMENT '状态：0-想去 1-去过 2-种草',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    is_favorite TINYINT DEFAULT 0 COMMENT '是否收藏',
    photo_count INT DEFAULT 0 COMMENT '照片数量',
    anniversary_id BIGINT DEFAULT NULL COMMENT '关联纪念日ID',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_status (status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='私密菜单表';

-- ----------------------------
-- 4. 美食笔记表
-- ----------------------------
DROP TABLE IF EXISTS t_food_note;
CREATE TABLE t_food_note (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    author_id BIGINT NOT NULL COMMENT '作者ID',
    title VARCHAR(256) NOT NULL COMMENT '笔记标题',
    content TEXT NOT NULL COMMENT '笔记内容',
    location VARCHAR(512) DEFAULT NULL COMMENT '位置信息',
    latitude DECIMAL(10,8) DEFAULT NULL COMMENT '纬度',
    longitude DECIMAL(11,8) DEFAULT NULL COMMENT '经度',
    is_anniversary_linked TINYINT DEFAULT 0 COMMENT '是否关联纪念日',
    anniversary_id BIGINT DEFAULT NULL COMMENT '关联的纪念日ID',
    view_count INT DEFAULT 0 COMMENT '查看次数',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    photo_urls TEXT COMMENT '照片URLs（JSON数组）',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_author_id (author_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='美食笔记表';

-- ----------------------------
-- 5. 纪念日表
-- ----------------------------
DROP TABLE IF EXISTS t_anniversary;
CREATE TABLE t_anniversary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    name VARCHAR(128) NOT NULL COMMENT '纪念日名称',
    anniversary_date DATE NOT NULL COMMENT '纪念日日期',
    anniversary_type TINYINT NOT NULL COMMENT '类型：1-相识 2-恋爱 3-表白 4-其他',
    remind_days_before TINYINT DEFAULT 7 COMMENT '提前提醒天数',
    auto_remind TINYINT DEFAULT 1 COMMENT '是否自动提醒',
    last_remind_date DATE DEFAULT NULL COMMENT '最后提醒日期',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_date (anniversary_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='纪念日表';

-- ----------------------------
-- 6. 投喂表
-- ----------------------------
DROP TABLE IF EXISTS t_feed;
CREATE TABLE t_feed (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    sender_id BIGINT NOT NULL COMMENT '发送者ID',
    receiver_id BIGINT NOT NULL COMMENT '接收者ID',
    feed_type VARCHAR(32) NOT NULL COMMENT '投喂类型：meal/dessert/snack/drink',
    content TEXT COMMENT '投喂内容描述',
    image_urls TEXT COMMENT '图片URLs（JSON数组）',
    message VARCHAR(256) DEFAULT NULL COMMENT '留言',
    status TINYINT DEFAULT 0 COMMENT '状态：0-待领取 1-已领取 2-已拒绝',
    expire_time DATETIME NOT NULL COMMENT '过期时间',
    reject_reason VARCHAR(256) DEFAULT NULL COMMENT '拒绝原因',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    receive_time DATETIME DEFAULT NULL COMMENT '领取时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_receiver_id (receiver_id),
    INDEX idx_status (status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='投喂表';

-- ----------------------------
-- 7. 心愿单表
-- ----------------------------
DROP TABLE IF EXISTS t_wish;
CREATE TABLE t_wish (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    wish_type VARCHAR(32) NOT NULL COMMENT '心愿类型：restaurant/dish/recipe',
    title VARCHAR(256) NOT NULL COMMENT '心愿标题',
    description TEXT COMMENT '心愿描述',
    image_url VARCHAR(1024) DEFAULT NULL COMMENT '图片',
    priority TINYINT DEFAULT 2 COMMENT '优先级：1-低 2-中 3-高',
    status TINYINT DEFAULT 0 COMMENT '状态：0-待实现 1-已实现 2-已过期',
    target_date DATE DEFAULT NULL COMMENT '目标日期',
    achieved_date DATE DEFAULT NULL COMMENT '实现日期',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_status (status),
    INDEX idx_target_date (target_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='心愿单表';

-- ----------------------------
-- 8. 通知表
-- ----------------------------
DROP TABLE IF EXISTS t_notification;
CREATE TABLE t_notification (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    type TINYINT NOT NULL COMMENT '通知类型：1-系统通知 2-互动通知 3-提醒通知',
    title VARCHAR(128) NOT NULL COMMENT '通知标题',
    content TEXT COMMENT '通知内容',
    related_id BIGINT DEFAULT NULL COMMENT '关联ID',
    related_type VARCHAR(32) DEFAULT NULL COMMENT '关联类型',
    sender_id BIGINT DEFAULT NULL COMMENT '发送者ID（用于互动通知）',
    is_read TINYINT DEFAULT 0 COMMENT '是否已读：0-未读 1-已读',
    read_time DATETIME DEFAULT NULL COMMENT '阅读时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_user_id (user_id),
    INDEX idx_type (type),
    INDEX idx_is_read (is_read),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知表';

-- ----------------------------
-- 9. 时光胶囊表
-- ----------------------------
DROP TABLE IF EXISTS t_time_capsule;
CREATE TABLE t_time_capsule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    capsule_type VARCHAR(32) NOT NULL COMMENT '胶囊类型：text/voice/video/photo',
    title VARCHAR(128) DEFAULT NULL COMMENT '胶囊标题',
    content TEXT COMMENT '胶囊内容',
    media_urls TEXT COMMENT '媒体URLs（JSON数组）',
    unlock_date DATE NOT NULL COMMENT '解锁日期',
    status TINYINT DEFAULT 0 COMMENT '状态：0-待解锁 1-已解锁',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    unlock_time DATETIME DEFAULT NULL COMMENT '解锁时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_unlock_date (unlock_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='时光胶囊表';

-- ----------------------------
-- 10. 心动时刻表
-- ----------------------------
DROP TABLE IF EXISTS t_heart_moment;
CREATE TABLE t_heart_moment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    moment_type VARCHAR(32) NOT NULL COMMENT '时刻类型：text/voice/photo',
    content TEXT COMMENT '内容',
    media_url VARCHAR(1024) DEFAULT NULL COMMENT '媒体URL',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_creator_id (creator_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='心动时刻表';

-- ----------------------------
-- 11. 打卡挑战表
-- ----------------------------
DROP TABLE IF EXISTS t_challenge;
CREATE TABLE t_challenge (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    partner_id BIGINT DEFAULT NULL COMMENT '挑战伙伴ID',
    challenge_type VARCHAR(32) NOT NULL COMMENT '挑战类型',
    title VARCHAR(128) NOT NULL COMMENT '挑战标题',
    description TEXT COMMENT '挑战描述',
    target_days INT DEFAULT 7 COMMENT '目标天数',
    current_days INT DEFAULT 0 COMMENT '当前天数',
    status TINYINT DEFAULT 0 COMMENT '状态：0-进行中 1-已完成 2-已失败 3-已取消',
    start_date DATE DEFAULT NULL COMMENT '开始日期',
    end_date DATE DEFAULT NULL COMMENT '结束日期',
    reward VARCHAR(256) DEFAULT NULL COMMENT '奖励',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='打卡挑战表';

-- ----------------------------
-- 12. 打卡记录表
-- ----------------------------
DROP TABLE IF EXISTS t_checkin_record;
CREATE TABLE t_checkin_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    challenge_id BIGINT NOT NULL COMMENT '挑战ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    checkin_date DATE NOT NULL COMMENT '打卡日期',
    content TEXT COMMENT '打卡内容',
    image_url VARCHAR(1024) DEFAULT NULL COMMENT '打卡图片',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_challenge_id (challenge_id),
    INDEX idx_user_id (user_id),
    INDEX idx_date (checkin_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='打卡记录表';

-- ----------------------------
-- 13. 照片表
-- ----------------------------
DROP TABLE IF EXISTS t_food_photo;
CREATE TABLE t_food_photo (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    note_id BIGINT DEFAULT NULL COMMENT '关联笔记ID',
    uploader_id BIGINT NOT NULL COMMENT '上传者ID',
    photo_url VARCHAR(1024) NOT NULL COMMENT '照片URL',
    thumbnail_url VARCHAR(1024) DEFAULT NULL COMMENT '缩略图URL',
    description VARCHAR(512) DEFAULT NULL COMMENT '照片描述',
    photo_date DATE DEFAULT NULL COMMENT '照片日期',
    location_name VARCHAR(256) DEFAULT NULL COMMENT '位置名称',
    latitude DECIMAL(10,8) DEFAULT NULL COMMENT '纬度',
    longitude DECIMAL(11,8) DEFAULT NULL COMMENT '经度',
    is_avatar TINYINT DEFAULT 0 COMMENT '是否设置为头像',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_uploader_id (uploader_id),
    INDEX idx_photo_date (photo_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='照片表';

-- ----------------------------
-- 14. 菜谱表
-- ----------------------------
DROP TABLE IF EXISTS t_recipe;
CREATE TABLE t_recipe (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    title VARCHAR(256) NOT NULL COMMENT '菜谱标题',
    cover_url VARCHAR(1024) DEFAULT NULL COMMENT '封面URL',
    description TEXT COMMENT '菜谱描述',
    ingredients TEXT COMMENT '食材（JSON数组）',
    steps TEXT COMMENT '制作步骤（JSON数组）',
    difficulty VARCHAR(16) DEFAULT NULL COMMENT '难度：easy/medium/hard',
    cooking_time INT DEFAULT NULL COMMENT '烹饪时间（分钟）',
    servings INT DEFAULT NULL COMMENT '份量',
    status TINYINT DEFAULT 0 COMMENT '状态：0-草稿 1-已发布',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    collect_count INT DEFAULT 0 COMMENT '收藏数',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜谱表';

-- ----------------------------
-- 15. 订单表
-- ----------------------------
DROP TABLE IF EXISTS t_order;
CREATE TABLE t_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    buyer_id BIGINT NOT NULL COMMENT '买家ID',
    seller_id BIGINT NOT NULL COMMENT '卖家ID',
    recipe_id BIGINT NOT NULL COMMENT '菜谱ID',
    recipe_name VARCHAR(256) NOT NULL COMMENT '菜谱名称',
    quantity INT DEFAULT 1 COMMENT '数量',
    total_amount DECIMAL(10,2) NOT NULL COMMENT '总价',
    address VARCHAR(512) DEFAULT NULL COMMENT '配送地址',
    status TINYINT DEFAULT 0 COMMENT '状态：0-待接单 1-制作中 2-待送达 3-已完成 4-已取消 5-退款中 6-已退款',
    remark TEXT COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    pay_time DATETIME DEFAULT NULL COMMENT '支付时间',
    accept_time DATETIME DEFAULT NULL COMMENT '接单时间',
    complete_time DATETIME DEFAULT NULL COMMENT '完成时间',
    cancel_time DATETIME DEFAULT NULL COMMENT '取消时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_buyer_id (buyer_id),
    INDEX idx_seller_id (seller_id),
    INDEX idx_status (status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';

-- ----------------------------
-- 16. 购物车表
-- ----------------------------
DROP TABLE IF EXISTS t_cart;
CREATE TABLE t_cart (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    recipe_id BIGINT NOT NULL COMMENT '菜谱ID',
    quantity INT DEFAULT 1 COMMENT '数量',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_recipe_id (recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='购物车表';

-- ----------------------------
-- 17. 点赞记录表
-- ----------------------------
DROP TABLE IF EXISTS t_like;
CREATE TABLE t_like (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    target_type VARCHAR(32) NOT NULL COMMENT '目标类型：menu/note/recipe',
    target_id BIGINT NOT NULL COMMENT '目标ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_user_target (user_id, target_type, target_id),
    INDEX idx_target (target_type, target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='点赞记录表';

-- ----------------------------
-- 18. 评论表
-- ----------------------------
DROP TABLE IF EXISTS t_comment;
CREATE TABLE t_comment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    target_type VARCHAR(32) NOT NULL COMMENT '目标类型：menu/note/recipe',
    target_id BIGINT NOT NULL COMMENT '目标ID',
    parent_id BIGINT DEFAULT NULL COMMENT '父评论ID',
    content TEXT NOT NULL COMMENT '评论内容',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_target (target_type, target_id),
    INDEX idx_user_id (user_id),
    INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论表';

-- ----------------------------
-- 初始化测试数据（可选）
-- ----------------------------
-- INSERT INTO t_user (openid, nick_name, avatar_url) VALUES ('test_openid_1', '小明', 'https://example.com/avatar1.jpg');
-- INSERT INTO t_user (openid, nick_name, avatar_url) VALUES ('test_openid_2', '小红', 'https://example.com/avatar2.jpg');

-- ----------------------------
-- 19. 情侣解绑记录表
-- ----------------------------
DROP TABLE IF EXISTS t_couple_unbind_record;
CREATE TABLE t_couple_unbind_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '原情侣关系ID',
    user1_id BIGINT NOT NULL COMMENT '用户1ID',
    user2_id BIGINT NOT NULL COMMENT '用户2ID',
    applicant_id BIGINT DEFAULT NULL COMMENT '申请解绑者ID',
    love_start_date DATETIME DEFAULT NULL COMMENT '恋爱开始日期',
    love_days INT DEFAULT 0 COMMENT '恋爱天数',
    couple_nickname VARCHAR(128) DEFAULT NULL COMMENT '情侣昵称',
    backup_data MEDIUMTEXT COMMENT '备份数据（JSON格式）',
    unbind_time DATETIME NOT NULL COMMENT '解绑时间',
    data_expire_time DATETIME NOT NULL COMMENT '数据过期时间',
    status TINYINT DEFAULT 0 COMMENT '状态：0-可恢复 1-已恢复 2-已过期清除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_user1 (user1_id),
    INDEX idx_user2 (user2_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情侣解绑记录表';

-- ----------------------------
-- 纪念日表新增字段（农历支持、提醒配置）
-- ----------------------------
-- ALTER TABLE t_anniversary ADD COLUMN is_lunar_date TINYINT DEFAULT 0 COMMENT '是否农历日期：0-阳历 1-农历';
-- ALTER TABLE t_anniversary ADD COLUMN lunar_month INT DEFAULT NULL COMMENT '农历月';
-- ALTER TABLE t_anniversary ADD COLUMN lunar_day INT DEFAULT NULL COMMENT '农历日';
-- ALTER TABLE t_anniversary ADD COLUMN remind_channels VARCHAR(64) DEFAULT 'app' COMMENT '提醒渠道：逗号分隔，如 app,wechat,sms';
-- ALTER TABLE t_anniversary ADD COLUMN remind_hour INT DEFAULT 9 COMMENT '提醒时间（小时）';
-- ALTER TABLE t_anniversary ADD COLUMN wechat_remind_enabled TINYINT DEFAULT 0 COMMENT '是否启用微信提醒';
-- ALTER TABLE t_anniversary ADD COLUMN sms_remind_enabled TINYINT DEFAULT 0 COMMENT '是否启用短信提醒';
-- ALTER TABLE t_anniversary ADD COLUMN app_remind_enabled TINYINT DEFAULT 1 COMMENT '是否启用APP推送';

-- ----------------------------
-- 心愿表新增字段（状态流转）
-- ----------------------------
-- ALTER TABLE t_wish ADD COLUMN viewer_id BIGINT DEFAULT NULL COMMENT '查看者ID';
-- ALTER TABLE t_wish ADD COLUMN view_time DATETIME DEFAULT NULL COMMENT '查看时间';
-- ALTER TABLE t_wish ADD COLUMN in_progress_time DATETIME DEFAULT NULL COMMENT '进行中开始时间';
-- ALTER TABLE t_wish MODIFY COLUMN status TINYINT DEFAULT 0 COMMENT '状态：0-待实现 1-进行中 2-已实现 3-已过期';
