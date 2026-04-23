-- Test data initialization
-- Add test data as needed for integration tests

-- Clean up existing data first (handles context reuse with shared H2 database)
DELETE FROM t_user WHERE id IN (1, 2);
DELETE FROM t_couple WHERE id = 1;

-- Insert a test couple relationship first
INSERT INTO t_couple (id, couple_code, user_1_id, user_2_id, start_date, love_days, status, create_time)
VALUES (1, 'TESTCODE', 1, 2, '2025-01-01', 100, 1, CURRENT_TIMESTAMP);

-- Insert test users with couple relationship
INSERT INTO t_user (id, openid, nick_name, avatar_url, status, couple_id, love_start_date)
VALUES (1, 'test_openid_001', '测试用户1', 'https://example.com/avatar1.jpg', 0, 1, CURRENT_TIMESTAMP);

INSERT INTO t_user (id, openid, nick_name, avatar_url, status, couple_id, love_start_date)
VALUES (2, 'test_openid_002', '测试用户2', 'https://example.com/avatar2.jpg', 0, 1, CURRENT_TIMESTAMP);
