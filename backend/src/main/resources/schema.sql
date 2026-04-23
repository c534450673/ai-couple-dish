-- 用户表
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

-- 情侣关系表
CREATE TABLE IF NOT EXISTS t_couple (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_code VARCHAR(32) DEFAULT NULL COMMENT '情侣码',
    user_1_id BIGINT NOT NULL COMMENT '用户1ID（发起方）',
    user_2_id BIGINT DEFAULT NULL COMMENT '用户2ID（确认方）',
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

-- 私密菜单表
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

-- 美食笔记表
CREATE TABLE IF NOT EXISTS t_food_note (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    author_id BIGINT NOT NULL COMMENT '作者ID',
    title VARCHAR(256) NOT NULL COMMENT '笔记标题',
    content TEXT NOT NULL COMMENT '笔记内容',
    location VARCHAR(512) DEFAULT NULL COMMENT '位置信息',
    latitude DECIMAL(10,8) DEFAULT NULL COMMENT '纬度',
    longitude DECIMAL(11,8) DEFAULT NULL COMMENT '经度',
    is_anniversary_linked TINYINT DEFAULT 0 COMMENT '是否关联纪念日',
    anniversary_id BIGINT DEFAULT NULL COMMENT '关联纪念日ID',
    view_count INT DEFAULT 0 COMMENT '查看次数',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    photo_urls TEXT DEFAULT NULL COMMENT '照片URL列表(JSON)',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_author_id (author_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='美食笔记表';

-- 纪念日表
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

-- 投喂表
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

-- 心愿单表
CREATE TABLE IF NOT EXISTS t_wish (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    wish_type VARCHAR(32) NOT NULL COMMENT '心愿类型：restaurant/dish/recipe',
    title VARCHAR(256) NOT NULL COMMENT '心愿标题',
    description TEXT COMMENT '心愿描述',
    image_url VARCHAR(1024) DEFAULT NULL COMMENT '图片',
    priority TINYINT DEFAULT 2 COMMENT '优先级：1-低 2-中 3-高',
    status TINYINT DEFAULT 0 COMMENT '状态：0-待实现 1-进行中 2-已实现 3-已过期',
    viewer_id BIGINT DEFAULT NULL COMMENT '查看者ID',
    view_time DATETIME DEFAULT NULL COMMENT '查看时间',
    in_progress_time DATETIME DEFAULT NULL COMMENT '进行中开始时间',
    target_date DATE DEFAULT NULL COMMENT '目标日期',
    achieved_date DATE DEFAULT NULL COMMENT '实现日期',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_status (status),
    INDEX idx_target_date (target_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='心愿单表';

-- 通知表
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

-- =====================================================
-- Phase 1: 核心功能补全
-- =====================================================

-- 每日问候表
CREATE TABLE IF NOT EXISTS t_daily_greeting (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    greeting_type TINYINT NOT NULL COMMENT '类型: 1-早安 2-晚安',
    content VARCHAR(512) DEFAULT NULL COMMENT '文字内容',
    voice_url VARCHAR(512) DEFAULT NULL COMMENT '语音文件URL',
    voice_duration INT DEFAULT NULL COMMENT '语音时长(秒)',
    greeting_date DATE NOT NULL COMMENT '问候日期',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_date (couple_id, greeting_date),
    INDEX idx_user_date (user_id, greeting_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日问候表';

-- 问候连续打卡记录表
CREATE TABLE IF NOT EXISTS t_greeting_streak (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    streak_type TINYINT NOT NULL COMMENT '类型: 1-早安连续 2-晚安连续',
    streak_days INT DEFAULT 0 COMMENT '连续天数',
    max_streak_days INT DEFAULT 0 COMMENT '最大连续天数',
    last_date DATE DEFAULT NULL COMMENT '最后打卡日期',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_couple_type (couple_id, streak_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问候连续打卡记录表';

-- 情侣爱心树表
CREATE TABLE IF NOT EXISTS t_couple_tree (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    level INT DEFAULT 1 COMMENT '等级',
    total_nutrient BIGINT DEFAULT 0 COMMENT '总养分',
    current_level_nutrient BIGINT DEFAULT 0 COMMENT '当前等级养分',
    skin_id VARCHAR(64) DEFAULT 'default' COMMENT '皮肤ID',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_couple_id (couple_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情侣爱心树表';

-- 树养分变动日志表
CREATE TABLE IF NOT EXISTS t_tree_nutrient_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    nutrient_amount INT NOT NULL COMMENT '养分数量',
    source_action VARCHAR(64) NOT NULL COMMENT '来源行为',
    remark VARCHAR(256) DEFAULT NULL COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_time (couple_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='树养分变动日志表';

-- 每日情侣任务表
CREATE TABLE IF NOT EXISTS t_daily_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    task_date DATE NOT NULL COMMENT '任务日期',
    task_type VARCHAR(64) NOT NULL COMMENT '任务类型',
    task_name VARCHAR(128) NOT NULL COMMENT '任务名称',
    task_description VARCHAR(512) DEFAULT NULL COMMENT '任务描述',
    target_count INT DEFAULT 1 COMMENT '目标数量',
    reward_nutrient INT NOT NULL COMMENT '奖励养分',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-进行中 1-已完成 2-已过期',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_date (couple_id, task_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日情侣任务表';

-- 用户任务进度表
CREATE TABLE IF NOT EXISTS t_user_task_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    current_count INT DEFAULT 0 COMMENT '当前进度',
    is_completed TINYINT DEFAULT 0 COMMENT '是否完成',
    complete_time DATETIME DEFAULT NULL COMMENT '完成时间',
    is_reward_claimed TINYINT DEFAULT 0 COMMENT '是否已领取奖励',
    reward_claim_time DATETIME DEFAULT NULL COMMENT '奖励领取时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_task_user (task_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户任务进度表';

-- 海报模板表
CREATE TABLE IF NOT EXISTS t_poster_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    template_code VARCHAR(64) NOT NULL COMMENT '模板编码',
    template_name VARCHAR(128) NOT NULL COMMENT '模板名称',
    template_type VARCHAR(64) NOT NULL COMMENT '类型: anniversary/feed/map/annual',
    template_config TEXT NOT NULL COMMENT '模板配置JSON',
    preview_url VARCHAR(512) DEFAULT NULL COMMENT '预览图URL',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE INDEX idx_template_code (template_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='海报模板表';

-- 用户海报表
CREATE TABLE IF NOT EXISTS t_user_poster (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    poster_type VARCHAR(64) NOT NULL COMMENT '海报类型',
    template_id BIGINT NOT NULL COMMENT '模板ID',
    poster_url VARCHAR(512) NOT NULL COMMENT '生成的海报URL',
    invite_code VARCHAR(64) DEFAULT NULL COMMENT '邀请码',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_user_time (user_id, create_time),
    INDEX idx_couple_time (couple_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户海报表';

-- 用户邀请码表
CREATE TABLE IF NOT EXISTS t_user_invite_code (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    invite_code VARCHAR(16) NOT NULL COMMENT '邀请码',
    invite_count INT DEFAULT 0 COMMENT '邀请人数',
    reward_amount DECIMAL(10,2) DEFAULT 0 COMMENT '奖励金额',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_user_id (user_id),
    UNIQUE INDEX idx_invite_code (invite_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户邀请码表';

-- 用户邀请关系表
CREATE TABLE IF NOT EXISTS t_user_referral (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    inviter_id BIGINT NOT NULL COMMENT '邀请人ID',
    invitee_id BIGINT NOT NULL COMMENT '被邀请人ID',
    invite_code VARCHAR(16) NOT NULL COMMENT '邀请码',
    register_time DATETIME NOT NULL COMMENT '注册时间',
    bind_couple_time DATETIME DEFAULT NULL COMMENT '绑定情侣时间',
    reward_status TINYINT DEFAULT 0 COMMENT '奖励状态: 0-待发放 1-已发放',
    reward_amount DECIMAL(10,2) DEFAULT 0 COMMENT '奖励金额',
    reward_time DATETIME DEFAULT NULL COMMENT '奖励发放时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_inviter (inviter_id),
    INDEX idx_invitee (invitee_id),
    INDEX idx_invite_code (invite_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户邀请关系表';

-- =====================================================
-- Phase 2: 重要功能实现
-- =====================================================

-- 心情记录表（情绪投递箱）
CREATE TABLE IF NOT EXISTS t_mood_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    mood_type VARCHAR(32) NOT NULL COMMENT '心情类型: happy/tired/upset/miss_you/love/sad/angry/anxious',
    description VARCHAR(512) DEFAULT NULL COMMENT '心情描述',
    mood_icon VARCHAR(32) DEFAULT NULL COMMENT '心情图标',
    mood_color VARCHAR(32) DEFAULT NULL COMMENT '心情颜色',
    record_date DATE NOT NULL COMMENT '记录日期',
    is_read TINYINT DEFAULT 0 COMMENT '是否已读: 0-未读 1-已读',
    read_time DATETIME DEFAULT NULL COMMENT '阅读时间',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_date (couple_id, record_date),
    INDEX idx_user_date (user_id, record_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='心情记录表';

-- 随机甜蜜炸弹表
CREATE TABLE IF NOT EXISTS t_sweet_bomb (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    bomb_type VARCHAR(64) NOT NULL COMMENT '类型: memory/data/festival/question',
    content TEXT NOT NULL COMMENT '炸弹内容JSON',
    sent_time DATETIME NOT NULL COMMENT '发送时间',
    is_read TINYINT DEFAULT 0 COMMENT '是否已读',
    is_answered TINYINT DEFAULT 0 COMMENT '是否已回答',
    answer_content TEXT DEFAULT NULL COMMENT '回答内容',
    answer_time DATETIME DEFAULT NULL COMMENT '回答时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_time (couple_id, sent_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='随机甜蜜炸弹表';

-- 深度问答题目库表
CREATE TABLE IF NOT EXISTS t_deep_question (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    week_number INT NOT NULL COMMENT '周数',
    question_text VARCHAR(512) NOT NULL COMMENT '问题内容',
    question_type VARCHAR(64) DEFAULT 'open' COMMENT '类型: open/choice',
    options TEXT DEFAULT NULL COMMENT '选项JSON',
    category VARCHAR(64) DEFAULT 'relationship' COMMENT '分类: relationship/future/values/dreams',
    sort_order INT DEFAULT 0 COMMENT '排序',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_week (week_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='深度问答题目库表';

-- 情侣问答进度表
CREATE TABLE IF NOT EXISTS t_couple_qa_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    current_week INT DEFAULT 1 COMMENT '当前周数',
    current_question INT DEFAULT 1 COMMENT '当前问题序号',
    total_completed INT DEFAULT 0 COMMENT '已完成问题数',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_couple (couple_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情侣问答进度表';

-- 深度问答答案表
CREATE TABLE IF NOT EXISTS t_deep_qa_answer (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    question_id BIGINT NOT NULL COMMENT '问题ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    answer_text TEXT NOT NULL COMMENT '答案内容',
    is_revealed TINYINT DEFAULT 0 COMMENT '是否已揭晓',
    reveal_time DATETIME DEFAULT NULL COMMENT '揭晓时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_question (couple_id, question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='深度问答答案表';

-- 关系气象站表
CREATE TABLE IF NOT EXISTS t_relationship_weather (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    weather_level VARCHAR(32) NOT NULL COMMENT '等级: sunny/cloudy/rainy/stormy',
    interaction_score INT DEFAULT 60 COMMENT '互动分数',
    days_since_last_interaction INT DEFAULT 0 COMMENT '距上次互动天数',
    temperature_score INT DEFAULT 60 COMMENT '恋爱温度',
    alert_sent TINYINT DEFAULT 0 COMMENT '是否已发送预警',
    alert_type VARCHAR(32) DEFAULT NULL COMMENT '预警类型',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_time (couple_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='关系气象站表';

-- 情侣段位表
CREATE TABLE IF NOT EXISTS t_couple_rank (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    current_rank VARCHAR(32) NOT NULL DEFAULT 'bronze' COMMENT '段位: bronze/silver/gold/platinum/diamond/king',
    rank_score INT DEFAULT 0 COMMENT '段位分数',
    consecutive_interaction_days INT DEFAULT 0 COMMENT '连续互动天数',
    temperature_score INT DEFAULT 60 COMMENT '恋爱温度',
    promotion_date DATETIME DEFAULT NULL COMMENT '最近晋升时间',
    demotion_warning TINYINT DEFAULT 0 COMMENT '降级预警',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_couple_id (couple_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情侣段位表';

-- =====================================================
-- 补充缺失的表
-- =====================================================

-- 时光胶囊表
CREATE TABLE IF NOT EXISTS t_time_capsule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    capsule_type VARCHAR(32) NOT NULL COMMENT '胶囊类型: text/voice/video/photo',
    title VARCHAR(256) NOT NULL COMMENT '胶囊标题',
    content TEXT COMMENT '胶囊内容',
    media_urls TEXT COMMENT '媒体URLs（JSON数组）',
    unlock_date DATE NOT NULL COMMENT '解锁日期',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-待解锁 1-已解锁',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    unlock_time DATETIME DEFAULT NULL COMMENT '解锁时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_unlock_date (unlock_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='时光胶囊表';

-- 心动时刻表
CREATE TABLE IF NOT EXISTS t_heart_moment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    moment_type VARCHAR(32) NOT NULL COMMENT '时刻类型: text/voice/photo',
    content TEXT COMMENT '内容',
    media_url VARCHAR(512) DEFAULT NULL COMMENT '媒体URL',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='心动时刻表';

-- 情侣解绑记录表
CREATE TABLE IF NOT EXISTS t_couple_unbind_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '原情侣关系ID',
    user_1_id BIGINT NOT NULL COMMENT '用户1ID',
    user_2_id BIGINT NOT NULL COMMENT '用户2ID',
    applicant_id BIGINT NOT NULL COMMENT '申请解绑者ID',
    love_start_date DATETIME DEFAULT NULL COMMENT '恋爱开始日期',
    love_days INT DEFAULT 0 COMMENT '恋爱天数',
    couple_nickname VARCHAR(128) DEFAULT NULL COMMENT '情侣昵称',
    backup_data TEXT COMMENT '备份数据（JSON格式）',
    unbind_time DATETIME DEFAULT NULL COMMENT '解绑时间',
    data_expire_time DATETIME DEFAULT NULL COMMENT '数据过期时间',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-已解绑可恢复 1-已恢复 2-已过期清除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_user_1 (user_1_id),
    INDEX idx_user_2 (user_2_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情侣解绑记录表';

-- 打卡挑战表
CREATE TABLE IF NOT EXISTS t_challenge (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    partner_id BIGINT NOT NULL COMMENT '挑战伙伴ID',
    challenge_type VARCHAR(64) NOT NULL COMMENT '挑战类型',
    title VARCHAR(256) NOT NULL COMMENT '挑战标题',
    description TEXT COMMENT '挑战描述',
    target_days INT NOT NULL COMMENT '目标天数',
    current_days INT DEFAULT 0 COMMENT '当前天数',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-进行中 1-已完成 2-已失败 3-已取消',
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE DEFAULT NULL COMMENT '结束日期',
    reward VARCHAR(256) DEFAULT NULL COMMENT '奖励',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='打卡挑战表';

-- 打卡记录表
CREATE TABLE IF NOT EXISTS t_checkin_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    challenge_id BIGINT NOT NULL COMMENT '挑战ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    checkin_date DATE NOT NULL COMMENT '打卡日期',
    content TEXT COMMENT '打卡内容',
    image_url VARCHAR(512) DEFAULT NULL COMMENT '打卡图片',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_challenge_id (challenge_id),
    INDEX idx_user_date (user_id, checkin_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='打卡记录表';

-- 菜谱表
CREATE TABLE IF NOT EXISTS t_recipe (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    title VARCHAR(256) NOT NULL COMMENT '菜谱标题',
    cover_url VARCHAR(512) DEFAULT NULL COMMENT '封面URL',
    description TEXT COMMENT '菜谱描述',
    ingredients TEXT COMMENT '食材（JSON数组）',
    steps TEXT COMMENT '制作步骤（JSON数组）',
    difficulty VARCHAR(32) DEFAULT 'medium' COMMENT '难度: easy/medium/hard',
    cooking_time INT DEFAULT NULL COMMENT '烹饪时间（分钟）',
    servings INT DEFAULT NULL COMMENT '份量',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-草稿 1-已发布',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    collect_count INT DEFAULT 0 COMMENT '收藏数',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜谱表';

-- 菜谱点赞关系表
CREATE TABLE IF NOT EXISTS t_recipe_like (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    recipe_id BIGINT NOT NULL COMMENT '菜谱ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_recipe_user (recipe_id, user_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜谱点赞关系表';

-- 菜谱收藏关系表
CREATE TABLE IF NOT EXISTS t_recipe_collect (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    recipe_id BIGINT NOT NULL COMMENT '菜谱ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_recipe_user (recipe_id, user_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜谱收藏关系表';

-- 订单表
CREATE TABLE IF NOT EXISTS t_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    couple_id BIGINT NOT NULL COMMENT '情侣ID',
    buyer_id BIGINT NOT NULL COMMENT '买家ID',
    seller_id BIGINT NOT NULL COMMENT '卖家ID',
    recipe_id BIGINT NOT NULL COMMENT '菜谱ID',
    recipe_name VARCHAR(256) NOT NULL COMMENT '菜谱名称',
    quantity INT DEFAULT 1 COMMENT '数量',
    total_amount DECIMAL(10,2) DEFAULT NULL COMMENT '总价',
    address VARCHAR(512) DEFAULT NULL COMMENT '配送地址',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-待接单 1-制作中 2-待送达 3-已完成 4-已取消 5-退款中 6-已退款',
    remark TEXT DEFAULT NULL COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    pay_time DATETIME DEFAULT NULL COMMENT '支付时间',
    accept_time DATETIME DEFAULT NULL COMMENT '接单时间',
    complete_time DATETIME DEFAULT NULL COMMENT '完成时间',
    cancel_time DATETIME DEFAULT NULL COMMENT '取消时间',
    INDEX idx_couple_id (couple_id),
    INDEX idx_buyer_id (buyer_id),
    INDEX idx_seller_id (seller_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';

-- 购物车表
CREATE TABLE IF NOT EXISTS t_cart (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    recipe_id BIGINT NOT NULL COMMENT '菜谱ID',
    quantity INT DEFAULT 1 COMMENT '数量',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='购物车表';
