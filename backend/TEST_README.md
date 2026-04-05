# 情侣私密菜单 - 测试说明

## 测试目录结构

```
backend/src/test/
├── java/com/aicoupledish/
│   ├── UserServiceTest.java           # 用户服务单元测试
│   ├── AnniversaryServiceTest.java     # 纪念日服务单元测试
│   ├── FeedServiceTest.java           # 投喂服务单元测试
│   ├── MenuServiceTest.java           # 菜单服务单元测试
│   └── CoupleServiceIntegrationTest.java  # 情侣服务集成测试
├── resources/
│   ├── application-test.yml           # 测试环境配置
│   └── test-data.sql                 # 测试数据初始化脚本
└── TEST_CASES.md                     # 测试用例文档
```

## 测试数据初始化

### 数据库初始化脚本

测试数据位于 `src/test/resources/test-data.sql`，包含：

| 用户ID | 昵称 | 状态 |
|--------|------|------|
| 1 | 小明 | 已绑定（情侣ID=1） |
| 2 | 小红 | 已绑定（情侣ID=1） |
| 3 | 小华 | 已绑定（情侣ID=2） |
| 4 | 小丽 | 已绑定（情侣ID=2） |

### 测试数据使用原则

1. **后端数据库初始语句**：所有测试数据通过 `test-data.sql` 初始化
2. **不使用前端mock数据**：前端不模拟任何数据，所有数据来自后端
3. **测试数据隔离**：测试环境使用独立的测试数据库 `ai_couple_dish_test`

## 运行测试

### 前提条件

1. MySQL 8.0+ 运行中
2. Redis 6.0+ 运行中
3. 创建测试数据库：

```sql
CREATE DATABASE IF NOT EXISTS ai_couple_dish_test DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 运行单元测试

```bash
cd backend

# 运行所有测试
mvn test

# 运行特定测试类
mvn test -Dtest=UserServiceTest
mvn test -Dtest=AnniversaryServiceTest
mvn test -Dtest=FeedServiceTest
mvn test -Dtest=MenuServiceTest
mvn test -Dtest=CoupleServiceIntegrationTest

# 运行特定测试方法
mvn test -Dtest=UserServiceTest#wechatLogin_NewUser_ShouldCreateUser
```

### 运行集成测试

```bash
# 运行带Spring Context的集成测试
mvn test -Dspring.profiles.active=test

# 运行特定集成测试类
mvn test -Dtest=CoupleServiceIntegrationTest -Dspring.profiles.active=test
```

## 测试用例覆盖

### 用户服务测试 (UserServiceTest)

| 测试用例 | 描述 |
|---------|------|
| wechatLogin_NewUser_ShouldCreateUser | 新用户首次登录创建用户 |
| wechatLogin_ExistingUser_ShouldUpdateUser | 老用户登录更新信息 |
| wechatLogin_NoOpenid_ShouldThrowException | 无openid抛异常 |
| getUserInfo_UserExists_ShouldReturnUserInfo | 获取用户信息成功 |
| getUserInfo_UserNotFound_ShouldThrowException | 用户不存在抛异常 |
| getUserInfo_CacheHit_ShouldReturnFromCache | 缓存命中 |
| updateUserInfo_UpdateNickname_ShouldSuccess | 更新昵称成功 |
| getUserIdByOpenid_CacheMiss_ShouldQueryDatabase | openid查询用户ID |

### 纪念日服务测试 (AnniversaryServiceTest)

| 测试用例 | 描述 |
|---------|------|
| getAnniversaryList_NotBindCouple_ShouldThrowException | 未绑定抛异常 |
| getAnniversaryList_WithAnniversaries_ShouldReturnList | 获取纪念日列表 |
| addAnniversary_LoveType_ShouldCheckDuplicate | 恋爱纪念日不能重复 |
| addAnniversary_MeetType_ShouldSuccess | 相识纪念日添加成功 |
| updateAnniversary_LoveTypeCannotChangeType_ShouldThrowException | 恋爱日类型不可改 |
| deleteAnniversary_LoveType_ShouldThrowException | 恋爱日不能删除 |
| deleteAnniversary_OtherType_ShouldSuccess | 其他纪念日可删除 |
| checkTodayAnniversary_TodayIsAnniversary_ShouldReturn | 今日纪念日检查 |

### 投喂服务测试 (FeedServiceTest)

| 测试用例 | 描述 |
|---------|------|
| getTodayFeedStatus_AlreadySent_ShouldReturnSentTrue | 今日已发送 |
| sendFeed_NotBindCouple_ShouldThrowException | 未绑定抛异常 |
| sendFeed_AlreadySentToday_ShouldThrowException | 今日已发送投喂 |
| sendFeed_MealType_ShouldSuccess | 发送正餐投喂 |
| sendFeed_DessertType_ShouldSuccess | 发送甜品投喂 |
| acceptFeed_ValidFeed_ShouldSuccess | 接受有效投喂 |
| acceptFeed_Expired_ShouldThrowException | 接受过期投喂抛异常 |
| rejectFeed_ValidRequest_ShouldSuccess | 拒绝投喂成功 |
| feedTypeName_Meal_ShouldReturn正餐 | 类型名称转换 |

### 菜单服务测试 (MenuServiceTest)

| 测试用例 | 描述 |
|---------|------|
| getMenuList_NotBindCouple_ShouldThrowException | 未绑定抛异常 |
| getMenuList_WithMenus_ShouldReturnList | 获取菜单列表 |
| getMenuList_FilterByStatusWant_ShouldReturnFilteredList | 按想去筛选 |
| getMenuDetail_MenuExists_ShouldReturnDetail | 获取菜单详情 |
| getMenuDetail_MenuNotFound_ShouldThrowException | 菜单不存在 |
| addMenu_WantType_ShouldSuccess | 添加想去菜单 |
| addMenu_BeenType_ShouldSuccess | 添加去过菜单 |
| updateMenu_MenuExists_ShouldSuccess | 更新菜单成功 |
| deleteMenu_MenuExists_ShouldSoftDelete | 软删除菜单 |
| likeMenu_MenuExists_ShouldSuccess | 点赞菜单 |
| unlikeMenu_ShouldDecrementLikeCount | 取消点赞 |
| favoriteMenu_ShouldSetFavoriteTrue | 收藏菜单 |
| getMenuStats_ShouldReturnCounts | 获取统计数据 |

### 情侣服务集成测试 (CoupleServiceIntegrationTest)

| 测试用例 | 描述 |
|---------|------|
| generateCoupleCode_UnboundUser_ShouldSuccess | 生成情侣码 |
| generateCoupleCode_AlreadyBound_ShouldThrowException | 已绑定抛异常 |
| bindCouple_ValidCode_ShouldSuccess | 有效码绑定成功 |
| bindCouple_InvalidCode_ShouldThrowException | 无效码抛异常 |
| getCoupleInfo_BoundCouple_ShouldReturnInfo | 获取情侣信息 |
| validateCoupleCode_ValidCode_ShouldReturnTrue | 有效码验证 |
| validateCoupleCode_ExpiredCode_ShouldReturnFalse | 过期码验证 |
| loveDaysCalculation_ShouldBeCorrect | 恋爱天数计算 |
| applyUnbind_ShouldRequireBothConfirm | 申请解绑 |
| confirmUnbind_BothConfirm_ShouldSuccess | 确认解绑 |
| rejectUnbind_ShouldRestoreStatus | 拒绝解绑恢复状态 |

## 测试数据初始化SQL

```sql
-- 运行测试数据初始化
mysql -u root -p ai_couple_dish_test < src/test/resources/test-data.sql
```

## 商业化测试要点

### 1. 真实环境测试
- 使用真实数据库而非mock
- 所有API通过HTTP调用测试
- 测试数据通过后端SQL初始化

### 2. 边界条件测试
- 情侣码8位格式验证
- 情侣码7天有效期验证
- 恋爱天数计算精度
- 菜单名称最大长度（100字）

### 3. 权限验证测试
- 非创建者不能编辑/删除菜单
- 非接收者不能领取/拒绝投喂
- 跨情侣数据隔离

### 4. 状态流转测试
- 投喂状态：待领取 → 已领取/已拒绝
- 菜单状态：想去 → 去过 → 种草
- 情侣状态：待确认 → 已绑定 → 申请解绑 → 已解除

### 5. 异常场景测试
- 情侣码过期
- 情侣码无效
- 今日已发送投喂
- 恋爱纪念日重复
- 恋爱日删除校验

## 持续集成

建议在CI/CD流程中：

1. 运行单元测试 `mvn test`
2. 集成测试使用专门的测试数据库
3. 测试覆盖率报告生成
4. 自动化回归测试

## 注意事项

1. 测试数据中的密码和敏感信息已脱敏
2. 测试数据库与生产数据库严格分离
3. 测试完成后清理测试数据
4. 并发测试需要注意数据隔离
