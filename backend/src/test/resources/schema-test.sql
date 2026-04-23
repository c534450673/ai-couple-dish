-- H2-compatible test schema
-- Note: H2 requires unique index names globally, so we prefix with table name

-- 用户表
CREATE TABLE IF NOT EXISTS t_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    openid VARCHAR(64) NOT NULL,
    nick_name VARCHAR(64) DEFAULT NULL,
    avatar_url VARCHAR(512) DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    gender TINYINT DEFAULT 0,
    couple_id BIGINT DEFAULT NULL,
    love_start_date DATETIME DEFAULT NULL,
    taste_preferences TEXT,
    food_restrictions TEXT,
    member_level TINYINT DEFAULT 0,
    status TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted TINYINT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_user_openid ON t_user(openid);
CREATE INDEX IF NOT EXISTS idx_user_couple_id ON t_user(couple_id);

-- 情侣关系表
CREATE TABLE IF NOT EXISTS t_couple (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_code VARCHAR(32) DEFAULT NULL,
    user_1_id BIGINT NOT NULL,
    user_2_id BIGINT DEFAULT NULL,
    start_date DATE DEFAULT NULL,
    love_days INT DEFAULT 0,
    couple_nickname VARCHAR(128) DEFAULT NULL,
    status TINYINT DEFAULT 0,
    unbind_applicant_id BIGINT DEFAULT NULL,
    unbind_apply_time DATETIME DEFAULT NULL,
    avatar_frame VARCHAR(64) DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_couple_code ON t_couple(couple_code);
CREATE INDEX IF NOT EXISTS idx_couple_user_1 ON t_couple(user_1_id);
CREATE INDEX IF NOT EXISTS idx_couple_user_2 ON t_couple(user_2_id);
CREATE INDEX IF NOT EXISTS idx_couple_status ON t_couple(status);

-- 私密菜单表
CREATE TABLE IF NOT EXISTS t_couple_menu (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    restaurant_name VARCHAR(256) NOT NULL,
    dish_name VARCHAR(256) DEFAULT NULL,
    dish_category VARCHAR(64) DEFAULT NULL,
    price DECIMAL(10,2) DEFAULT NULL,
    location VARCHAR(512) DEFAULT NULL,
    latitude DECIMAL(10,8) DEFAULT NULL,
    longitude DECIMAL(11,8) DEFAULT NULL,
    note TEXT,
    rating TINYINT DEFAULT NULL,
    eater_ids VARCHAR(512) DEFAULT NULL,
    eaten_date DATE DEFAULT NULL,
    status TINYINT DEFAULT 0,
    like_count INT DEFAULT 0,
    is_favorite TINYINT DEFAULT 0,
    photo_urls TEXT DEFAULT NULL,
    photo_count INT DEFAULT 0,
    anniversary_id BIGINT DEFAULT NULL,
    is_deleted TINYINT DEFAULT 0,
    delete_time DATETIME DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_menu_couple_id ON t_couple_menu(couple_id);
CREATE INDEX IF NOT EXISTS idx_menu_status ON t_couple_menu(status);
CREATE INDEX IF NOT EXISTS idx_menu_create_time ON t_couple_menu(create_time);

-- 美食笔记表
CREATE TABLE IF NOT EXISTS t_food_note (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    title VARCHAR(256) NOT NULL,
    content TEXT NOT NULL,
    location VARCHAR(512) DEFAULT NULL,
    latitude DECIMAL(10,8) DEFAULT NULL,
    longitude DECIMAL(11,8) DEFAULT NULL,
    is_anniversary_linked TINYINT DEFAULT 0,
    anniversary_id BIGINT DEFAULT NULL,
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    photo_urls TEXT DEFAULT NULL,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_note_couple_id ON t_food_note(couple_id);
CREATE INDEX IF NOT EXISTS idx_note_author_id ON t_food_note(author_id);
CREATE INDEX IF NOT EXISTS idx_note_create_time ON t_food_note(create_time);

-- 纪念日表
CREATE TABLE IF NOT EXISTS t_anniversary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    name VARCHAR(128) NOT NULL,
    anniversary_date DATE NOT NULL,
    is_lunar_date TINYINT DEFAULT 0,
    lunar_month TINYINT DEFAULT NULL,
    lunar_day TINYINT DEFAULT NULL,
    anniversary_type TINYINT NOT NULL,
    remind_days_before TINYINT DEFAULT 7,
    auto_remind TINYINT DEFAULT 1,
    last_remind_date DATE DEFAULT NULL,
    remind_channels VARCHAR(128) DEFAULT NULL,
    remind_hour TINYINT DEFAULT NULL,
    wechat_remind_enabled TINYINT DEFAULT 0,
    sms_remind_enabled TINYINT DEFAULT 0,
    app_remind_enabled TINYINT DEFAULT 0,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_anniv_couple_id ON t_anniversary(couple_id);
CREATE INDEX IF NOT EXISTS idx_anniv_date ON t_anniversary(anniversary_date);

-- 投喂表
CREATE TABLE IF NOT EXISTS t_feed (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    receiver_id BIGINT NOT NULL,
    feed_type VARCHAR(32) NOT NULL,
    content TEXT,
    image_urls TEXT,
    message VARCHAR(256) DEFAULT NULL,
    status TINYINT DEFAULT 0,
    expire_time DATETIME NOT NULL,
    reject_reason VARCHAR(256) DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    receive_time DATETIME DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_feed_couple_id ON t_feed(couple_id);
CREATE INDEX IF NOT EXISTS idx_feed_sender_id ON t_feed(sender_id);
CREATE INDEX IF NOT EXISTS idx_feed_receiver_id ON t_feed(receiver_id);
CREATE INDEX IF NOT EXISTS idx_feed_status ON t_feed(status);
CREATE INDEX IF NOT EXISTS idx_feed_create_time ON t_feed(create_time);

-- 心愿单表
CREATE TABLE IF NOT EXISTS t_wish (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    wish_type VARCHAR(32) NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT,
    image_url VARCHAR(1024) DEFAULT NULL,
    priority TINYINT DEFAULT 2,
    status TINYINT DEFAULT 0,
    viewer_id BIGINT DEFAULT NULL,
    view_time DATETIME DEFAULT NULL,
    in_progress_time DATETIME DEFAULT NULL,
    target_date DATE DEFAULT NULL,
    achieved_date DATE DEFAULT NULL,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wish_couple_id ON t_wish(couple_id);
CREATE INDEX IF NOT EXISTS idx_wish_status ON t_wish(status);
CREATE INDEX IF NOT EXISTS idx_wish_target_date ON t_wish(target_date);

-- 通知表
CREATE TABLE IF NOT EXISTS t_notification (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    type TINYINT NOT NULL,
    title VARCHAR(128) NOT NULL,
    content TEXT,
    related_id BIGINT DEFAULT NULL,
    related_type VARCHAR(32) DEFAULT NULL,
    sender_id BIGINT DEFAULT NULL,
    is_read TINYINT DEFAULT 0,
    read_time DATETIME DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notif_user_id ON t_notification(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_type ON t_notification(type);
CREATE INDEX IF NOT EXISTS idx_notif_is_read ON t_notification(is_read);
CREATE INDEX IF NOT EXISTS idx_notif_create_time ON t_notification(create_time);

-- 每日问候表
CREATE TABLE IF NOT EXISTS t_daily_greeting (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    greeting_type TINYINT NOT NULL,
    content VARCHAR(512) DEFAULT NULL,
    voice_url VARCHAR(512) DEFAULT NULL,
    voice_duration INT DEFAULT NULL,
    greeting_date DATE NOT NULL,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_greeting_couple_date ON t_daily_greeting(couple_id, greeting_date);
CREATE INDEX IF NOT EXISTS idx_greeting_user_date ON t_daily_greeting(user_id, greeting_date);

-- 问候连续打卡记录表
CREATE TABLE IF NOT EXISTS t_greeting_streak (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    streak_type TINYINT NOT NULL,
    streak_days INT DEFAULT 0,
    max_streak_days INT DEFAULT 0,
    last_date DATE DEFAULT NULL,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_streak_couple_type ON t_greeting_streak(couple_id, streak_type);

-- 情侣爱心树表
CREATE TABLE IF NOT EXISTS t_couple_tree (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    level INT DEFAULT 1,
    total_nutrient BIGINT DEFAULT 0,
    current_level_nutrient BIGINT DEFAULT 0,
    skin_id VARCHAR(64) DEFAULT 'default',
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tree_couple_id ON t_couple_tree(couple_id);

-- 树养分变动日志表
CREATE TABLE IF NOT EXISTS t_tree_nutrient_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    nutrient_amount INT NOT NULL,
    source_action VARCHAR(64) NOT NULL,
    remark VARCHAR(256) DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nutrient_couple_time ON t_tree_nutrient_log(couple_id, create_time);

-- 每日情侣任务表
CREATE TABLE IF NOT EXISTS t_daily_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    task_date DATE NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    task_name VARCHAR(128) NOT NULL,
    task_description VARCHAR(512) DEFAULT NULL,
    target_count INT DEFAULT 1,
    reward_nutrient INT NOT NULL,
    status TINYINT DEFAULT 0,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_couple_date ON t_daily_task(couple_id, task_date);

-- 用户任务进度表
CREATE TABLE IF NOT EXISTS t_user_task_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    current_count INT DEFAULT 0,
    is_completed TINYINT DEFAULT 0,
    complete_time DATETIME DEFAULT NULL,
    is_reward_claimed TINYINT DEFAULT 0,
    reward_claim_time DATETIME DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_progress_task_user ON t_user_task_progress(task_id, user_id);

-- 海报模板表
CREATE TABLE IF NOT EXISTS t_poster_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    template_code VARCHAR(64) NOT NULL,
    template_name VARCHAR(128) NOT NULL,
    template_type VARCHAR(64) NOT NULL,
    template_config TEXT NOT NULL,
    preview_url VARCHAR(512) DEFAULT NULL,
    is_active TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_template_code ON t_poster_template(template_code);

-- 用户海报表
CREATE TABLE IF NOT EXISTS t_user_poster (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    couple_id BIGINT NOT NULL,
    poster_type VARCHAR(64) NOT NULL,
    template_id BIGINT NOT NULL,
    poster_url VARCHAR(512) NOT NULL,
    invite_code VARCHAR(64) DEFAULT NULL,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_poster_user_time ON t_user_poster(user_id, create_time);
CREATE INDEX IF NOT EXISTS idx_poster_couple_time ON t_user_poster(couple_id, create_time);

-- 用户邀请码表
CREATE TABLE IF NOT EXISTS t_user_invite_code (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    invite_code VARCHAR(16) NOT NULL,
    invite_count INT DEFAULT 0,
    reward_amount DECIMAL(10,2) DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_invite_user_id ON t_user_invite_code(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invite_code ON t_user_invite_code(invite_code);

-- 用户邀请关系表
CREATE TABLE IF NOT EXISTS t_user_referral (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    inviter_id BIGINT NOT NULL,
    invitee_id BIGINT NOT NULL,
    invite_code VARCHAR(16) NOT NULL,
    register_time DATETIME NOT NULL,
    bind_couple_time DATETIME DEFAULT NULL,
    reward_status TINYINT DEFAULT 0,
    reward_amount DECIMAL(10,2) DEFAULT 0,
    reward_time DATETIME DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_referral_inviter ON t_user_referral(inviter_id);
CREATE INDEX IF NOT EXISTS idx_referral_invitee ON t_user_referral(invitee_id);
CREATE INDEX IF NOT EXISTS idx_referral_code ON t_user_referral(invite_code);

-- 心情记录表
CREATE TABLE IF NOT EXISTS t_mood_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    couple_id BIGINT NOT NULL,
    mood_type VARCHAR(32) NOT NULL,
    description VARCHAR(512) DEFAULT NULL,
    mood_icon VARCHAR(32) DEFAULT NULL,
    mood_color VARCHAR(32) DEFAULT NULL,
    record_date DATE NOT NULL,
    is_read TINYINT DEFAULT 0,
    read_time DATETIME DEFAULT NULL,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mood_couple_date ON t_mood_record(couple_id, record_date);
CREATE INDEX IF NOT EXISTS idx_mood_user_date ON t_mood_record(user_id, record_date);

-- 随机甜蜜炸弹表
CREATE TABLE IF NOT EXISTS t_sweet_bomb (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    bomb_type VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    sent_time DATETIME NOT NULL,
    is_read TINYINT DEFAULT 0,
    is_answered TINYINT DEFAULT 0,
    answer_content TEXT DEFAULT NULL,
    answer_time DATETIME DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bomb_couple_time ON t_sweet_bomb(couple_id, sent_time);

-- 深度问答题目库表
CREATE TABLE IF NOT EXISTS t_deep_question (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    week_number INT NOT NULL,
    question_text VARCHAR(512) NOT NULL,
    question_type VARCHAR(64) DEFAULT 'open',
    options TEXT DEFAULT NULL,
    category VARCHAR(64) DEFAULT 'relationship',
    sort_order INT DEFAULT 0,
    is_active TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_question_week ON t_deep_question(week_number);

-- 情侣问答进度表
CREATE TABLE IF NOT EXISTS t_couple_qa_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    current_week INT DEFAULT 1,
    current_question INT DEFAULT 1,
    total_completed INT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_qa_couple ON t_couple_qa_progress(couple_id);

-- 深度问答答案表
CREATE TABLE IF NOT EXISTS t_deep_qa_answer (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    answer_text TEXT NOT NULL,
    is_revealed TINYINT DEFAULT 0,
    reveal_time DATETIME DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_answer_couple_question ON t_deep_qa_answer(couple_id, question_id);

-- 关系气象站表
CREATE TABLE IF NOT EXISTS t_relationship_weather (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    weather_level VARCHAR(32) NOT NULL,
    interaction_score INT DEFAULT 60,
    days_since_last_interaction INT DEFAULT 0,
    temperature_score INT DEFAULT 60,
    alert_sent TINYINT DEFAULT 0,
    alert_type VARCHAR(32) DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weather_couple_time ON t_relationship_weather(couple_id, create_time);

-- 情侣段位表
CREATE TABLE IF NOT EXISTS t_couple_rank (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    current_rank VARCHAR(32) NOT NULL DEFAULT 'bronze',
    rank_score INT DEFAULT 0,
    consecutive_interaction_days INT DEFAULT 0,
    temperature_score INT DEFAULT 60,
    promotion_date DATETIME DEFAULT NULL,
    demotion_warning TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rank_couple_id ON t_couple_rank(couple_id);

-- 时光胶囊表
CREATE TABLE IF NOT EXISTS t_time_capsule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    capsule_type VARCHAR(32) NOT NULL,
    title VARCHAR(256) NOT NULL,
    content TEXT,
    media_urls TEXT,
    unlock_date DATE NOT NULL,
    status TINYINT DEFAULT 0,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    unlock_time DATETIME DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_capsule_couple_id ON t_time_capsule(couple_id);
CREATE INDEX IF NOT EXISTS idx_capsule_unlock_date ON t_time_capsule(unlock_date);

-- 心动时刻表
CREATE TABLE IF NOT EXISTS t_heart_moment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    moment_type VARCHAR(32) NOT NULL,
    content TEXT,
    media_url VARCHAR(512) DEFAULT NULL,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_moment_couple_id ON t_heart_moment(couple_id);
CREATE INDEX IF NOT EXISTS idx_moment_create_time ON t_heart_moment(create_time);

-- 情侣解绑记录表
CREATE TABLE IF NOT EXISTS t_couple_unbind_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    user_1_id BIGINT NOT NULL,
    user_2_id BIGINT NOT NULL,
    applicant_id BIGINT NOT NULL,
    love_start_date DATETIME DEFAULT NULL,
    love_days INT DEFAULT 0,
    couple_nickname VARCHAR(128) DEFAULT NULL,
    backup_data TEXT,
    unbind_time DATETIME DEFAULT NULL,
    data_expire_time DATETIME DEFAULT NULL,
    status TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_unbind_couple_id ON t_couple_unbind_record(couple_id);
CREATE INDEX IF NOT EXISTS idx_unbind_user_1 ON t_couple_unbind_record(user_1_id);
CREATE INDEX IF NOT EXISTS idx_unbind_user_2 ON t_couple_unbind_record(user_2_id);

-- 打卡挑战表
CREATE TABLE IF NOT EXISTS t_challenge (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    partner_id BIGINT NOT NULL,
    challenge_type VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT,
    target_days INT NOT NULL,
    current_days INT DEFAULT 0,
    status TINYINT DEFAULT 0,
    start_date DATE NOT NULL,
    end_date DATE DEFAULT NULL,
    reward VARCHAR(256) DEFAULT NULL,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_challenge_couple_id ON t_challenge(couple_id);
CREATE INDEX IF NOT EXISTS idx_challenge_status ON t_challenge(status);

-- 打卡记录表
CREATE TABLE IF NOT EXISTS t_checkin_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    challenge_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    checkin_date DATE NOT NULL,
    content TEXT,
    image_url VARCHAR(512) DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_checkin_challenge_id ON t_checkin_record(challenge_id);
CREATE INDEX IF NOT EXISTS idx_checkin_user_date ON t_checkin_record(user_id, checkin_date);

-- 菜谱表
CREATE TABLE IF NOT EXISTS t_recipe (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    title VARCHAR(256) NOT NULL,
    cover_url VARCHAR(512) DEFAULT NULL,
    description TEXT,
    ingredients TEXT,
    steps TEXT,
    difficulty VARCHAR(32) DEFAULT 'medium',
    cooking_time INT DEFAULT NULL,
    servings INT DEFAULT NULL,
    status TINYINT DEFAULT 0,
    like_count INT DEFAULT 0,
    collect_count INT DEFAULT 0,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recipe_user_id ON t_recipe(user_id);
CREATE INDEX IF NOT EXISTS idx_recipe_status ON t_recipe(status);

-- 菜谱点赞关系表
CREATE TABLE IF NOT EXISTS t_recipe_like (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    recipe_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_like_unique ON t_recipe_like(recipe_id, user_id);
CREATE INDEX IF NOT EXISTS idx_recipe_like_user_id ON t_recipe_like(user_id);

-- 菜谱收藏关系表
CREATE TABLE IF NOT EXISTS t_recipe_collect (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    recipe_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_collect_unique ON t_recipe_collect(recipe_id, user_id);
CREATE INDEX IF NOT EXISTS idx_recipe_collect_user_id ON t_recipe_collect(user_id);

-- 订单表
CREATE TABLE IF NOT EXISTS t_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    buyer_id BIGINT NOT NULL,
    seller_id BIGINT NOT NULL,
    recipe_id BIGINT NOT NULL,
    recipe_name VARCHAR(256) NOT NULL,
    quantity INT DEFAULT 1,
    total_amount DECIMAL(10,2) DEFAULT NULL,
    address VARCHAR(512) DEFAULT NULL,
    status TINYINT DEFAULT 0,
    remark TEXT DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    pay_time DATETIME DEFAULT NULL,
    accept_time DATETIME DEFAULT NULL,
    complete_time DATETIME DEFAULT NULL,
    cancel_time DATETIME DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_couple_id ON t_order(couple_id);
CREATE INDEX IF NOT EXISTS idx_order_buyer_id ON t_order(buyer_id);
CREATE INDEX IF NOT EXISTS idx_order_seller_id ON t_order(seller_id);
CREATE INDEX IF NOT EXISTS idx_order_status ON t_order(status);

-- 购物车表
CREATE TABLE IF NOT EXISTS t_cart (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    recipe_id BIGINT NOT NULL,
    quantity INT DEFAULT 1,
    is_deleted TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cart_user_id ON t_cart(user_id);

-- 笔记点赞表
CREATE TABLE IF NOT EXISTS t_note_like (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    note_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_note_like_unique ON t_note_like(note_id, user_id);
CREATE INDEX IF NOT EXISTS idx_note_like_user_id ON t_note_like(user_id);

-- 恋爱日历表
CREATE TABLE IF NOT EXISTS t_love_calendar (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    couple_id BIGINT NOT NULL,
    calendar_date DATE NOT NULL,
    event_type VARCHAR(32) DEFAULT NULL,
    event_title VARCHAR(256) DEFAULT NULL,
    event_content TEXT,
    is_anniversary TINYINT DEFAULT 0,
    anniversary_id BIGINT DEFAULT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_calendar_couple_date ON t_love_calendar(couple_id, calendar_date);
