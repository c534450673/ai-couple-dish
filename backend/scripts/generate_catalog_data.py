import json
from pathlib import Path

cuisines = json.loads(Path("data/catalog/cuisines.json").read_text())
dish_names = [
    "宫保鸡丁",
    "麻婆豆腐",
    "回锅肉",
    "鱼香肉丝",
    "水煮鱼",
    "辣子鸡",
    "糖醋排骨",
    "白切鸡",
    "叉烧",
    "豉汁蒸排骨",
    "盐焗鸡",
    "煲仔饭",
    "葱烧海参",
    "九转大肠",
    "糖醋鲤鱼",
    "油焖大虾",
    "松鼠鳜鱼",
    "清炖狮子头",
    "西湖醋鱼",
    "龙井虾仁",
    "佛跳墙",
    "荔枝肉",
    "沙茶面",
    "剁椒鱼头",
    "腊味合蒸",
    "臭鳜鱼",
    "徽州毛豆腐",
    "寿司",
    "天妇罗",
    "拉面",
    "烤肉",
    "泡菜锅",
    "石锅拌饭",
    "冬阴功汤",
    "海南鸡饭",
    "越南春卷",
    "希腊沙拉",
    "海鲜饭",
    "意大利面",
    "披萨",
    "汉堡",
    "烤牛排",
]
dishes = []
for i in range(320):
    cuisine = cuisines[i % len(cuisines)]
    dishes.append(
        {
            "slug": f"{cuisine['slug']}-dish-{i + 1:03d}",
            "name": f"{dish_names[i % len(dish_names)]}（{cuisine['name']}）",
            "cuisine": cuisine["slug"],
            "tags": ["家常", "推荐"],
            "spicyLevel": i % 4,
            "status": "draft",
            "sources": [],
        }
    )
Path("data/catalog/dishes.json").write_text(json.dumps(dishes, ensure_ascii=False, indent=2) + "\n")
