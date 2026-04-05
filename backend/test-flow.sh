#!/bin/bash

# 测试配置
BASE_URL="http://localhost:8080/api"
TEST_PHONE="13800001005"

echo "========================================"
echo "情侣私密菜单 全流程测试 (100次循环)"
echo "========================================"

# 创建新测试用户
echo ""
echo "[步骤1] 创建新测试用户..."
LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/user/phoneLogin?phone=${TEST_PHONE}")
TOKEN=$(echo $LOGIN_RESP | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
USER_ID=$(echo $LOGIN_RESP | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
NICKNAME=$(echo $LOGIN_RESP | grep -o '"nickName":"[^"]*"' | cut -d'"' -f4)

echo "用户ID: $USER_ID"
echo "昵称: $NICKNAME"

if [ -z "$TOKEN" ]; then
    echo "❌ Token获取失败"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

echo ""
echo "========================================"
echo "开始测试循环 (共100次)"
echo "========================================"

SUCCESS_COUNT=0
FAIL_COUNT=0

for i in $(seq 1 100); do
    echo ""
    echo "--- 第 ${i}/100 次测试循环 ---"

    # 1. 获取用户信息
    echo -n "[$i] /user/info ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/user/info" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 2. 获取情侣首页数据
    echo -n "[$i] /couple/home ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/couple/home" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 3. 获取恋爱计时
    echo -n "[$i] /couple/loveTimer ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/couple/loveTimer" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 4. 获取情侣信息
    echo -n "[$i] /couple/info ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/couple/info" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 5. 获取菜单列表
    echo -n "[$i] /menu/list ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/menu/list?status=0" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 6. 获取菜单统计
    echo -n "[$i] /menu/stats ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/menu/stats" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 7. 获取纪念日列表
    echo -n "[$i] /anniversary/list ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/anniversary/list" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 8. 获取投喂今日状态
    echo -n "[$i] /feed/today ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/feed/today" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 9. 获取收到的投喂列表
    echo -n "[$i] /feed/received ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/feed/received" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 10. 获取发出的投喂列表
    echo -n "[$i] /feed/sent ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/feed/sent" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # 11. 获取通知列表
    echo -n "[$i] /notification/list ... "
    if curl -s -H "$AUTH_HEADER" "${BASE_URL}/notification/list" | grep -q '"code":200'; then
        echo "✓"
    else
        echo "❌"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    echo "  >>> 第 ${i} 次循环完成 ✓"

    # 每10次循环输出一次进度
    if [ $((i % 10)) -eq 0 ]; then
        echo ""
        echo "========================================"
        echo "进度报告: 已完成 ${i}/100 次循环"
        echo "本次循环成功: ${SUCCESS_COUNT}, 失败: ${FAIL_COUNT}"
        echo "========================================"
    fi

    sleep 0.05
done

echo ""
echo "========================================"
echo "测试完成！"
echo "总循环次数: 100"
echo "成功: ${SUCCESS_COUNT}"
echo "失败: ${FAIL_COUNT}"
echo "========================================"

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 所有API测试通过！"
else
    echo "⚠️  有 ${FAIL_COUNT} 个测试用例失败"
fi
