# 情侣私密菜单 - 全流程体验测试计划

## 项目概述
AI Couple Dish 是一款面向情侣的私密菜单管理应用，支持记录约会餐厅、管理心愿清单、纪念日提醒等功能。

## 技术栈
- 后端: Java 17 + Spring Boot 2.7 + MySQL + Redis + JWT
- 前端H5: Vue 3 + Vite + Vant (运行在 http://localhost:3000)
- 后端API: http://localhost:8080/api

## 测试账号
- 情侣A: openid=test_couple_A, userId=1, 昵称=情侣小A
- 情侣B: openid=test_couple_B, userId=2, 昵称=情侣小B

## 体验流程 (按情侣使用场景排序)

### 阶段1: 注册登录与情侣绑定
1. **用户A登录** - 通过微信code登录
2. **用户B登录** - 通过微信code登录
3. **A生成情侣码** - /api/couple/generateCode
4. **B验证情侣码** - /api/couple/validateCode
5. **B绑定A** - /api/couple/bind
6. **查看情侣信息** - /api/couple/info
7. **查看恋爱计时** - /api/couple/loveTimer
8. **查看情侣主页** - /api/couple/home

### 阶段2: 私密菜单管理
9. **A添加菜单** - /api/menu/add (餐厅名、地址、评分等)
10. **B查看菜单列表** - /api/menu/list
11. **B查看菜单详情** - /api/menu/detail/{id}
12. **B点赞菜单** - /api/menu/like/{id}
13. **B收藏菜单** - /api/menu/favorite/{id}
14. **A更新菜单** - /api/menu/update/{id}
15. **A查看附近餐厅** - /api/menu/nearby
16. **A查看菜单统计** - /api/menu/stats
17. **A查看餐厅地图** - /api/menu/map

### 阶段3: 投喂功能
18. **A发送投喂** - /api/feed/send
19. **B查看收到的投喂** - /api/feed/received
20. **B接受投喂** - /api/feed/accept/{id}
21. **B查看今日投喂** - /api/feed/today
22. **A查看已发送投喂** - /api/feed/sent

### 阶段4: 纪念日管理
23. **A添加纪念日** - /api/anniversary/add
24. **B查看纪念日列表** - /api/anniversary/list
25. **查看即将到来的纪念日** - /api/anniversary/upcoming
26. **查看今日纪念日** - /api/anniversary/today
27. **查看下一个纪念日** - /api/anniversary/next

### 阶段5: 心愿单
28. **A添加心愿** - /api/wish/add
29. **B查看心愿列表** - /api/wish/list
30. **B完成心愿** - /api/wish/fulfill/{id}
31. **A更新心愿** - /api/wish/update/{id}

### 阶段6: 美食笔记
32. **A创建笔记** - /api/note/add
33. **B查看笔记列表** - /api/note/list
34. **B点赞笔记** - /api/note/like/{id}
35. **B评论笔记** - /api/note/comment/{id}

### 阶段7: 互动功能
36. **A发送甜蜜炸弹** - /api/sweetBomb/generate
37. **B查看未读甜蜜炸弹** - /api/sweetBomb/unread
38. **B回答甜蜜炸弹** - /api/sweetBomb/answer/{id}
39. **A创建时间胶囊** - /api/timeCapsule/create
40. **B查看时间胶囊** - /api/timeCapsule/list
41. **A发送每日问候** - /api/dailyGreeting/send
42. **B查看今日问候** - /api/dailyGreeting/today/status
43. **A发送心情** - /api/mood/send
44. **B查看未读心情** - /api/mood/unread/count

### 阶段8: 高级功能
45. **查看情侣树** - /api/coupleTree/info
46. **A浇水** - /api/coupleTree/water
47. **查看情侣排名** - /api/coupleRank/info
48. **查看关系天气** - /api/relationshipWeather/current
49. **A创建挑战** - /api/challenge/create
50. **B接受挑战** - /api/challenge/accept/{id}
51. **查看深层次问答** - /api/deepQa/current
52. **查看购物车** - /api/cart/list
53. **创建订单** - /api/order/create
54. **A生成海报** - /api/poster/generate
55. **查看邀请码** - /api/invite/code
56. **查看爱历** - /api/loveCalendar/month

### 阶段9: 通知与设置
57. **查看通知列表** - /api/notification/list
58. **查看未读通知数** - /api/notification/unreadCount
59. **标记通知已读** - /api/notification/read/{id}
60. **更新用户信息** - /api/user/update

## Bug报告格式
对于发现的每个问题，记录：
- 阶段和步骤编号
- 请求的API和参数
- 预期行为
- 实际行为(错误信息、返回码等)
- 严重程度: P0(阻塞) / P1(严重) / P2(一般) / P3(轻微)

## 数据库密码
Zsb4151994516! (root@127.0.0.1:3306/ai_couple_dish)
