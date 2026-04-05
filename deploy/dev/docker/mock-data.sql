-- 情侣私密菜单 - 本地开发Mock数据
-- 使用: mysql -u root -proot ai_couple_dish < mock-data.sql

USE ai_couple_dish;

-- ----------------------------
-- 1. 用户数据 (4个用户 - 2对情侣)
-- ----------------------------
INSERT INTO t_user (id, openid, nick_name, avatar_url, phone, gender, couple_id, love_start_date, member_level, status) VALUES
(1, 'openid_xm_001', '小明', 'https://api.dicebear.com/7.x/avataaars/svg?seed=xm', '13800001001', 1, 1, '2025-11-11 00:00:00', 0, 0),
(2, 'openid_xh_001', '小红', 'https://api.dicebear.com/7.x/avataaars/svg?seed=xh', '13800001002', 2, 1, '2025-11-11 00:00:00', 0, 0),
(3, 'openid_zw_001', '张三', 'https://api.dicebear.com/7.x/avataaars/svg?seed=zw', '13800001003', 1, 2, '2026-01-01 00:00:00', 0, 0),
(4, 'openid lw_001', '李四', 'https://api.dicebear.com/7.x/avataaars/svg?seed=lw', '13800001004', 2, 2, '2026-01-01 00:00:00', 0, 0);

-- ----------------------------
-- 2. 情侣关系数据
-- ----------------------------
INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, user_1_nickname, user_2_nickname, user_1_avatar, user_2_avatar, start_date, love_days, couple_nickname, status) VALUES
(1, 'COUPLE001', 1, 2, '小明', '小红', 'https://api.dicebear.com/7.x/avataaars/svg?seed=xm', 'https://api.dicebear.com/7.x/avataaars/svg?seed=xh', '2025-11-11', 130, '明红CP', 1),
(2, 'COUPLE002', 3, 4, '张三', '李四', 'https://api.dicebear.com/7.x/avataaars/svg?seed=zw', 'https://api.dicebear.com/7.x/avataaars/svg?seed=lw', '2026-01-01', 79, '三四CP', 1);

-- ----------------------------
-- 3. 私密菜单数据
-- ----------------------------
INSERT INTO t_couple_menu (id, couple_id, creator_id, restaurant_name, dish_name, dish_category, price, location, rating, status, like_count, is_favorite, eaten_date) VALUES
(1, 1, 1, '太二酸菜鱼', '酸菜鱼、水煮肉片', '川菜', 68.00, '深圳市南山区科兴科学园', 5, 1, 10, 1, '2026-03-15'),
(2, 1, 1, '陶陶居', '虾饺、凤爪、叉烧包', '粤菜', 88.00, '深圳市南山区万象天地', 5, 1, 8, 1, '2026-03-10'),
(3, 1, 2, '海底捞火锅', '毛肚、虾滑、牛肉卷', '火锅', 150.00, '深圳市南山区海岸城', 4, 1, 12, 0, '2026-03-05'),
(4, 1, 1, '奈雪の茶', '霸气芝士草莓', '甜品', 35.00, '深圳市南山区万象天地', 4, 2, 5, 1, NULL),
(5, 1, 2, '探鱼', '烤鱼、炭烤牛蛙', '川菜', 98.00, '深圳市龙华区壹方城', 4, 1, 7, 0, '2026-02-28'),
(6, 1, 1, '点都德', '红肠粉、虾饺皇', '粤菜', 75.00, '广州市天河区太古汇', 5, 1, 9, 1, '2026-02-20'),
(7, 1, 2, '西贝莜面村', '莜面鱼鱼牛大骨', '西北菜', 89.00, '深圳市南山区科兴科学园', 4, 1, 6, 0, '2026-02-14'),
(8, 1, 1, '木屋烧烤', '烤串、烤生蚝', '烧烤', 80.00, '深圳市南山区白石洲', 4, 1, 8, 1, '2026-02-10'),
-- 想去
(9, 1, 1, '润园四季椰子鸡', '椰子鸡、煲仔饭', '粤菜', 120.00, '深圳市南山区深圳湾万象城', NULL, 0, 0, 0, NULL),
(10, 1, 2, '绿茶餐厅', '面包诱惑、绿茶烤鸡', '江浙菜', 60.00, '深圳市南山区万象天地', NULL, 0, 0, 0, NULL),
(11, 1, 1, '客语-客家菜', '客家酿豆腐、盐焗鸡', '客家菜', 70.00, '深圳市龙华区壹方城', NULL, 0, 0, 0, NULL),
-- 种草
(12, 1, 2, '喜庭海鲜自助', '海鲜自助', '自助餐', 168.00, '深圳市南山区海岸城', 5, 2, 15, 1, NULL),
(13, 1, 1, '蛙来哒', '炭烤牛蛙、紫苏牛蛙', '川菜', 79.00, '深圳市南山区万象天地', 4, 2, 10, 0, NULL);

-- ----------------------------
-- 4. 纪念日数据
-- ----------------------------
INSERT INTO t_anniversary (id, couple_id, creator_id, name, anniversary_date, anniversary_type, remind_days_before, auto_remind) VALUES
(1, 1, 1, '恋爱纪念日', '2025-11-11', 2, 7, 1),
(2, 1, 1, '相识纪念日', '2025-05-01', 1, 3, 1),
(3, 1, 2, '100天纪念', '2026-02-19', 4, 1, 1),
(4, 1, 1, '一周年纪念', '2026-11-11', 2, 30, 1),
(5, 2, 3, '恋爱纪念日', '2026-01-01', 2, 7, 1);

-- ----------------------------
-- 5. 投喂数据
-- ----------------------------
INSERT INTO t_feed (id, couple_id, sender_id, receiver_id, feed_type, content, message, status, expire_time) VALUES
(1, 1, 1, 2, 'meal', '今天给你点了外卖，记得吃哦', '爱你哟~', 1, DATE_ADD(NOW(), INTERVAL 24 HOUR)),
(2, 1, 2, 1, 'dessert', '下午茶甜品 - 草莓慕斯蛋糕', '甜甜的~', 1, DATE_ADD(NOW(), INTERVAL 24 HOUR)),
(3, 1, 1, 2, 'snack', '零食大礼包', '解馋~', 0, DATE_ADD(NOW(), INTERVAL 24 HOUR)),
(4, 1, 2, 1, 'drink', '奶茶一杯 - 芋泥波波', '好喝~', 0, DATE_ADD(NOW(), INTERVAL 24 HOUR));

-- ----------------------------
-- 6. 美食笔记数据
-- ----------------------------
INSERT INTO t_food_note (id, couple_id, author_id, title, content, location_name, view_count, like_count, comment_count, status) VALUES
(1, 1, 1, '太二酸菜鱼探店', '今天和小红去了太二酸菜鱼，鱼片很嫩，酸度刚好，推荐大家去试试！', '深圳市南山区科兴科学园', 128, 15, 3, 1),
(2, 1, 2, '陶陶居早茶记', '周末和男朋友去喝早茶，虾饺皇太好吃了，皮薄馅大！', '深圳市南山区万象天地', 256, 22, 8, 1),
(3, 1, 1, '海底捞生日惊喜', '小红生日，带她去海底捞过生日，服务真的太棒了！', '深圳市南山区海岸城', 512, 45, 12, 1),
(4, 1, 2, '奈雪新品测评', '霸气芝士草莓回归啦！还是那个味道，超级好喝！', '深圳市南山区万象天地', 89, 12, 2, 1);

-- ----------------------------
-- 7. 心愿单数据
-- ----------------------------
INSERT INTO t_wish (id, couple_id, creator_id, wish_type, title, description, priority, status) VALUES
(1, 1, 1, 'restaurant', '去润园四季吃椰子鸡', '听说椰子鸡很鲜甜，想带小红去尝尝', 2, 0),
(2, 1, 2, 'dish', '学做酸菜鱼', '太二酸菜鱼太好吃了，想学着做给男朋友吃', 3, 0),
(3, 1, 1, 'restaurant', '去广州点都德', '广州老字号早茶店，一直想去', 2, 0),
(4, 1, 2, 'recipe', '研究新菜谱', '想学做几道拿手菜', 1, 1);

-- ----------------------------
-- 8. 通知数据
-- ----------------------------
INSERT INTO t_notification (id, user_id, type, title, content, related_id, is_read, create_time) VALUES
(1, 1, 2, '💕 收到点赞', '你的菜单「太二酸菜鱼」收到了一个赞', 1, 1, NOW()),
(2, 2, 2, '💕 收到点赞', '你的菜单「海底捞火锅」收到了一个赞', 3, 0, NOW()),
(3, 1, 3, '📅 纪念日提醒', '明天是恋爱纪念日哦，记得准备惊喜！', 1, 0, NOW()),
(4, 2, 3, '📅 纪念日提醒', '后天是100天纪念日！', 3, 0, NOW()),
(5, 1, 2, '🍰 收到投喂', '你的伴侣给你送了一份甜品，快去看看吧！', 2, 0, NOW());

-- 显示导入结果
SELECT 'Mock data imported successfully!' AS Status;
SELECT 'Users: ' AS Info, COUNT(*) AS Count FROM t_user;
SELECT 'Couples: ' AS Info, COUNT(*) AS Count FROM t_couple;
SELECT 'Menus: ' AS Info, COUNT(*) AS Count FROM t_couple_menu;
SELECT 'Anniversaries: ' AS Info, COUNT(*) AS Count FROM t_anniversary;
SELECT 'Feeds: ' AS Info, COUNT(*) AS Count FROM t_feed;
SELECT 'Notes: ' AS Info, COUNT(*) AS Count FROM t_food_note;
SELECT 'Wishes: ' AS Info, COUNT(*) AS Count FROM t_wish;
SELECT 'Notifications: ' AS Info, COUNT(*) AS Count FROM t_notification;
