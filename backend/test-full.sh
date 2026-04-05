#!/bin/bash

# 测试配置
BASE_URL="http://localhost:8080/api"
TEST_PHONE="13800001005"

echo "========================================"
echo "情侣私密菜单 全流程完整测试 (100次循环)"
echo "========================================"

# 创建新测试用户
echo ""
echo "[步骤1] 创建新测试用户..."
LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/user/phoneLogin?phone=${TEST_PHONE}")
TOKEN=$(echo $LOGIN_RESP | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
USER_ID=$(echo $LOGIN_RESP | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

echo "用户ID: $USER_ID"

if [ -z "$TOKEN" ]; then
    echo "❌ Token获取失败"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

echo ""
echo "========================================"
echo "开始100次完整测试循环"
echo "========================================"

SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_TESTS=$((100 * 13))

for i in $(seq 1 100); do
    # 1. 用户信息
    echo -n "[$i] /user/info ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/user/info" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 2. 情侣首页
    echo -n "[$i] /couple/home ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/couple/home" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 3. 恋爱计时
    echo -n "[$i] /couple/loveTimer ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/couple/loveTimer" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 4. 情侣信息
    echo -n "[$i] /couple/info ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/couple/info" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 5. 菜单列表
    echo -n "[$i] /menu/list ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/menu/list" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 6. 菜单统计
    echo -n "[$i] /menu/stats ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/menu/stats" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 7. 纪念日列表
    echo -n "[$i] /anniversary/list ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/anniversary/list" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 8. 投喂今日状态
    echo -n "[$i] /feed/today ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/feed/today" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 9. 收到的投喂
    echo -n "[$i] /feed/received ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/feed/received" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 10. 发出的投喂
    echo -n "[$i] /feed/sent ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/feed/sent" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 11. 通知列表
    echo -n "[$i] /notification/list ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/notification/list" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 12. 心愿单列表
    echo -n "[$i] /wish/list ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/wish/list" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    # 13. 笔记列表
    echo -n "[$i] /note/list ... "
    curl -s -H "$AUTH_HEADER" "${BASE_URL}/note/list" | grep -q '"code":200' && echo "✓" || { echo "❌"; FAIL_COUNT=$((FAIL_COUNT + 1)); continue; }

    SUCCESS_COUNT=$((SUCCESS_COUNT + 13))

    if [ $((i % 10)) -eq 0 ]; then
        echo ""
        echo "========================================"
        echo "进度: ${i}/100 次循环, 累计成功: ${SUCCESS_COUNT}/${TOTAL_TESTS}"
        echo "========================================"
    fi

    sleep 0.05
done

echo ""
echo "========================================"
echo "测试完成！"
echo "总循环次数: 100"
echo "成功测试数: ${SUCCESS_COUNT}/${TOTAL_TESTS}"
echo "失败测试数: ${FAIL_COUNT}"
echo "成功率: $((SUCCESS_COUNT * 100 / TOTAL_TESTS))%"
echo "========================================"

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 所有API测试通过！"
else
    echo "⚠️  有 ${FAIL_COUNT} 个测试用例失败"
fi
