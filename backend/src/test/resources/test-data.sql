-- 情侣私密菜单 V1.0 测试数据初始化脚本
-- 注意：此脚本仅用于测试环境，商业化测试使用真实数据库

USE ai_couple_dish;

-- ----------------------------
-- 清理旧数据（测试用）
-- ----------------------------
DELETE FROM t_time_capsule;
DELETE FROM t_heart_moment;
DELETE FROM t_challenge;
DELETE FROM t_checkin_record;
DELETE FROM t_food_photo;
DELETE FROM t_recipe;
DELETE FROM t_order;
DELETE FROM t_cart;
DELETE FROM t_like;
DELETE FROM t_comment;
DELETE FROM t_wish;
DELETE FROM t_feed;
DELETE FROM t_notification;
DELETE FROM t_anniversary;
DELETE FROM t_food_note;
DELETE FROM t_couple_menu;
DELETE FROM t_couple;
DELETE FROM t_user;

-- ----------------------------
-- 1. 初始化测试用户数据
-- ----------------------------
INSERT INTO t_user (id, openid, nick_name, avatar_url, phone, gender, couple_id, love_start_date, taste_preferences, food_restrictions, member_level, status) VALUES
(1, 'test_openid_user1', '小明', 'https://example.com/avatar1.jpg', '13800000001', 1, NULL, NULL, '["川菜","火锅"]', '["海鲜"]', 1, 0),
(2, 'test_openid_user2', '小红', 'https://example.com/avatar2.jpg', '13800000002', 2, NULL, NULL, '["粤菜","甜品"]', '["辣"]', 1, 0),
(3, 'test_openid_user3', '小华', 'https://example.com/avatar3.jpg', '13800000003', 1, NULL, NULL, NULL, NULL, 0, 0),
(4, 'test_openid_user4', '小丽', 'https://example.com/avatar4.jpg', '13800000004', 2, NULL, NULL, NULL, NULL, 0, 0);

-- ----------------------------
-- 2. 初始化已绑定情侣数据
-- ----------------------------
INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, user_1_nickname, user_2_nickname, user_1_avatar, user_2_avatar, start_date, love_days, couple_nickname, status, pending_user_id, code_expire_time) VALUES
(1, 'TEST1234', 1, 2, '小明', '小红', 'https://example.com/avatar1.jpg', 'https://example.com/avatar2.jpg', '2025-11-11', 130, '小明&小红', 1, NULL, '2026-03-28 00:00:00'),
(2, 'EXPIRED1', 3, 4, '小华', '小丽', 'https://example.com/avatar3.jpg', 'https://example.com/avatar4.jpg', '2025-06-01', 270, '小华&小丽', 1, NULL, '2025-03-01 00:00:00');

-- 更新用户的情侣ID
UPDATE t_user SET couple_id = 1 WHERE id IN (1, 2);
UPDATE t_user SET couple_id = 2 WHERE id IN (3, 4);
UPDATE t_user SET love_start_date = '2025-11-11' WHERE id IN (1, 2);
UPDATE t_user SET love_start_date = '2025-06-01' WHERE id IN (3, 4);

-- ----------------------------
-- 3. 初始化待确认状态的情侣数据（用于测试绑定流程）
-- ----------------------------
INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, start_date, love_days, status, pending_user_id, code_expire_time) VALUES
(3, 'PENDING1', 1, NULL, NULL, 0, 0, 1, '2026-03-28 00:00:00');

-- ----------------------------
-- 4. 初始化私密菜单数据
-- ----------------------------
INSERT INTO t_couple_menu (id, couple_id, creator_id, restaurant_name, dish_name, dish_category, price, location, latitude, longitude, note, rating, eater_ids, eaten_date, status, like_count, is_favorite, photo_count) VALUES
(1, 1, 1, '太二酸菜鱼', '酸菜鱼', '川菜', 68.00, '深圳市南山区科兴科学园', 22.54323, 113.95400, '鱼片很嫩，酸度刚好', 5, '[1,2]', '2026-03-15', 1, 5, 1, 3),
(2, 1, 2, '凑凑火锅', '火锅套餐', '火锅', 120.00, '深圳市南山区万象天地', 22.53456, 113.93876, '适合约会', 4, '[1,2]', '2026-02-14', 1, 3, 0, 5),
(3, 1, 1, '寿司大日本料理', '三文鱼刺身', '日料', 200.00, '深圳市福田区coco park', 22.52345, 113.94567, '三文鱼超新鲜', 5, '[1,2]', '2026-03-10', 1, 8, 1, 4),
(4, 1, 2, '陶陶居', '早茶点心', '粤菜', 80.00, '深圳市南山区海岸城', 22.53123, 113.94123, '虾饺很好吃', 4, '[1]', NULL, 0, 1, 0, 0),
(5, 1, 1, '奈雪の茶', '芋泥啵啵', '甜品', 35.00, '深圳市南山区科兴科学园', 22.54323, 113.95400, NULL, 5, '[2]', NULL, 2, 2, 1, 2);

-- ----------------------------
-- 5. 初始化纪念日数据
-- ----------------------------
INSERT INTO t_anniversary (id, couple_id, creator_id, name, anniversary_date, anniversary_type, remind_days_before, auto_remind) VALUES
(1, 1, 1, '恋爱纪念日', '2025-11-11', 2, 7, 1),
(2, 1, 1, '100天纪念', '2026-02-19', 4, 3, 1),
(3, 1, 2, '相识纪念', '2025-05-01', 1, 7, 0),
(4, 1, 1, '七夕节', '2025-08-10', 4, 7, 1),
(5, 2, 3, '恋爱纪念日', '2025-06-01', 2, 7, 1);

-- ----------------------------
-- 6. 初始化美食笔记数据
-- ----------------------------
INSERT INTO t_food_note (id, couple_id, author_id, title, content, location_name, latitude, longitude, is_anniversary_linked, anniversary_id, view_count, like_count, comment_count, photo_urls, status) VALUES
(1, 1, 1, '今天和他去了那家日料店', '三文鱼刺身超新鲜！强烈推荐', '寿司大日本料理', 22.52345, 113.94567, 0, NULL, 45, 12, 3, '["https://example.com/photo1.jpg","https://example.com/photo2.jpg"]', 1),
(2, 1, 2, '纪念我们在一起的第100天', '终于等到这一天啦！', '陶陶居', 22.53123, 113.94123, 1, 2, 89, 32, 8, '["https://example.com/photo3.jpg"]', 1),
(3, 1, 1, '周末约会日常', '和TA一起吃火锅，很幸福', '凑凑火锅', 22.53456, 113.93876, 0, NULL, 23, 8, 2, NULL, 1);

-- ----------------------------
-- 7. 初始化投喂数据
-- ----------------------------
INSERT INTO t_feed (id, couple_id, sender_id, receiver_id, feed_type, content, image_urls, message, status, expire_time, create_time, receive_time) VALUES
(1, 1, 1, 2, 'meal', '今天给你点了外卖，记得吃哦', '["https://example.com/meal1.jpg"]', '爱你哟', 1, '2026-03-22 20:00:00', '2026-03-21 10:00:00', '2026-03-21 11:30:00'),
(2, 1, 2, 1, 'dessert', '下午茶甜品', '["https://example.com/dessert1.jpg"]', '辛苦啦~', 0, '2026-03-22 18:00:00', '2026-03-21 14:00:00', NULL),
(3, 1, 1, 2, 'snack', '零食大礼包', NULL, '想你啦', 2, '2026-03-20 12:00:00', '2026-03-19 09:00:00', NULL),
(4, 1, 2, 1, 'drink', '奶茶一杯', '["https://example.com/drink1.jpg"]', '给你充充电', 1, '2026-03-21 20:00:00', '2026-03-20 15:00:00', '2026-03-20 16:00:00');

-- ----------------------------
-- 8. 初始化心愿单数据
-- ----------------------------
INSERT INTO t_wish (id, couple_id, creator_id, wish_type, title, description, priority, status, target_date) VALUES
(1, 1, 1, 'restaurant', '去广州吃早茶', '听说广州的早茶很正宗', 3, 0, '2026-05-01'),
(2, 1, 2, 'dish', '学会做酸菜鱼', '在家复刻太二酸菜鱼', 2, 0, '2026-06-01'),
(3, 1, 1, 'recipe', '一起做蛋糕', '周末在家做烘焙', 2, 1, '2026-02-14');

-- ----------------------------
-- 9. 初始化通知数据
-- ----------------------------
INSERT INTO t_notification (id, user_id, type, title, content, related_id, related_type, sender_id, is_read, create_time) VALUES
(1, 2, 2, '收到投喂', '你的伴侣给你送了一份正餐，快去看看吧！', 1, 'feed', 1, 0, '2026-03-21 10:00:00'),
(2, 1, 2, '投喂被接受', '你的投喂被接受了，快去看看TA的反应吧！', 1, 'feed', 2, 1, '2026-03-21 11:30:00'),
(3, 2, 2, '💕 收到点赞', '你的菜单「太二酸菜鱼」收到了一个赞', 1, 'menu', 1, 0, '2026-03-20 15:00:00'),
(4, 1, 1, '系统通知', '欢迎使用情侣私密菜单', NULL, NULL, NULL, 1, '2026-03-01 09:00:00');

-- ----------------------------
-- 10. 时光胶囊测试数据
-- ----------------------------
INSERT INTO t_time_capsule (id, couple_id, creator_id, capsule_type, title, content, unlock_date, status) VALUES
(1, 1, 1, 'text', '给未来的我们', '希望我们能一直在一起', '2027-03-21', 0),
(2, 1, 2, 'photo', '一周年纪念', 'https://example.com/capsule_photo.jpg', '2026-11-11', 0);

-- ----------------------------
-- 11. 心动时刻测试数据
-- ----------------------------
INSERT INTO t_heart_moment (id, couple_id, creator_id, moment_type, content, media_url) VALUES
(1, 1, 1, 'text', '今天的火锅很好吃', NULL),
(2, 1, 2, 'photo', NULL, 'https://example.com/moment1.jpg');
