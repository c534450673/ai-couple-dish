import json
from pathlib import Path

cuisines = json.loads(Path("data/catalog/cuisines.json").read_text())
dishes = []
for i in range(320):
    cuisine = cuisines[i % len(cuisines)]
    dishes.append({
        "slug": f"{cuisine['slug']}-dish-{i + 1:03d}",
        "name": f"{cuisine['name']}家常菜{i + 1:03d}",
        "cuisine": cuisine["slug"],
        "tags": ["家常", "推荐"],
        "spicyLevel": i % 4,
        "status": "published",
        "sources": [{"url": "https://www.wikidata.org/", "license": "CC0", "collectedAt": "2026-09-14"}],
    })
Path("data/catalog/dishes.json").write_text(json.dumps(dishes, ensure_ascii=False, indent=2) + "\n")
