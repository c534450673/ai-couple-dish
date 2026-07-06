USE ai_couple_dish;

ALTER TABLE t_anniversary ADD COLUMN is_lunar_date TINYINT DEFAULT 0;
ALTER TABLE t_anniversary ADD COLUMN lunar_month INT DEFAULT NULL;
ALTER TABLE t_anniversary ADD COLUMN lunar_day INT DEFAULT NULL;
ALTER TABLE t_anniversary ADD COLUMN remind_channels VARCHAR(64) DEFAULT 'app';
ALTER TABLE t_anniversary ADD COLUMN remind_hour INT DEFAULT 9;
ALTER TABLE t_anniversary ADD COLUMN wechat_remind_enabled TINYINT DEFAULT 0;
ALTER TABLE t_anniversary ADD COLUMN sms_remind_enabled TINYINT DEFAULT 0;
ALTER TABLE t_anniversary ADD COLUMN app_remind_enabled TINYINT DEFAULT 1;

ALTER TABLE t_couple_menu ADD COLUMN photo_urls TEXT;

ALTER TABLE t_wish ADD COLUMN viewer_id BIGINT DEFAULT NULL;
ALTER TABLE t_wish ADD COLUMN view_time DATETIME DEFAULT NULL;
ALTER TABLE t_wish ADD COLUMN in_progress_time DATETIME DEFAULT NULL;
