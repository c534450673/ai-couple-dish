-- 情侣私密菜单 - 开发环境数据库初始化脚本
-- 此脚本在MySQL容器首次启动时自动执行

USE ai_couple_dish;

-- ----------------------------
-- 1. 用户表
-- ----------------------------
CREATE TABLE IF NOT EXISTS t_user (
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
CREATE TABLE IF NOT EXISTS t_couple (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_code VARCHAR(32) DEFAULT NULL COMMENT '情侣码',
    user_1_id BIGINT NOT NULL COMMENT '用户1ID（发起方）',
    user_2_id BIGINT DEFAULT NULL COMMENT '用户2ID（确认方）',
    user_1_nickname VARCHAR(64) DEFAULT NULL COMMENT '用户1昵称（冗余）',
    user_2_nickname VARCHAR(64) DEFAULT NULL COMMENT '用户2昵称（冗余）',
    user_1_avatar VARCHAR(512) DEFAULT NULL COMMENT '用户1头像URL（冗余）',
    user_2_avatar VARCHAR(512) DEFAULT NULL COMMENT '用户2头像URL（冗余）',
    start_date DATE DEFAULT NULL COMMENT '恋爱开始日期',
    love_days INT DEFAULT 0 COMMENT '恋爱天数',
    couple_nickname VARCHAR(128) DEFAULT NULL COMMENT '情侣昵称',
    status TINYINT DEFAULT 0 COMMENT '状态：0-待确认 1-已绑定 2-已解除 3-申请解绑中',
    pending_user_id BIGINT DEFAULT NULL COMMENT '待确认方用户ID',
    code_expire_time DATETIME DEFAULT NULL COMMENT '情侣码过期时间',
    unbind_applicant_id BIGINT DEFAULT NULL COMMENT '解绑申请者ID',
    unbind_time DATETIME DEFAULT NULL COMMENT '解绑申请时间',
    unbind_deadline DATETIME DEFAULT NULL COMMENT '解绑确认截止时间',
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
CREATE TABLE IF NOT EXISTS t_couple_menu (
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
CREATE TABLE IF NOT EXISTS t_food_note (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    author_id BIGINT NOT NULL COMMENT '作者ID',
    title VARCHAR(256) NOT NULL COMMENT '笔记标题',
    content TEXT NOT NULL COMMENT '笔记内容',
    note_type TINYINT DEFAULT 0 COMMENT '笔记类型：0-美食记录 1-心情随笔 2-约会日记',
    location_name VARCHAR(256) DEFAULT NULL COMMENT '位置名称',
    latitude DECIMAL(10,8) DEFAULT NULL COMMENT '纬度',
    longitude DECIMAL(11,8) DEFAULT NULL COMMENT '经度',
    cover_photo_url VARCHAR(1024) DEFAULT NULL COMMENT '封面照片URL',
    eater_ids VARCHAR(256) DEFAULT NULL COMMENT '用餐人ID列表',
    photo_count INT DEFAULT 0 COMMENT '照片数量',
    view_count INT DEFAULT 0 COMMENT '查看次数',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    is_anniversary_linked TINYINT DEFAULT 0 COMMENT '是否关联纪念日',
    anniversary_id BIGINT DEFAULT NULL COMMENT '关联纪念日ID',
    linked_menu_ids VARCHAR(1024) DEFAULT NULL COMMENT '关联菜单ID列表',
    status TINYINT DEFAULT 1 COMMENT '状态：0-草稿 1-已发布',
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
CREATE TABLE IF NOT EXISTS t_anniversary (
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
CREATE TABLE IF NOT EXISTS t_feed (
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
CREATE TABLE IF NOT EXISTS t_wish (
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
CREATE TABLE IF NOT EXISTS t_notification (
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
CREATE TABLE IF NOT EXISTS t_time_capsule (
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
CREATE TABLE IF NOT EXISTS t_heart_moment (
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

SELECT 'Development database initialized successfully!' AS Status;
