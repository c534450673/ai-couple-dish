import json
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/catalog/dishes.json")
dishes = json.loads(path.read_text())
slugs = [dish.get("slug") for dish in dishes]
invalid = 0
seen_urls = set()
for dish in dishes:
    sources = dish.get("sources") or []
    if not dish.get("slug") or not sources:
        invalid += 1
        continue
    for source in sources:
        required = (
            source.get("url"),
            source.get("license"),
            source.get("attribution"),
            source.get("reviewStatus"),
        )
        if not all(required) or source["url"] in seen_urls:
            invalid += 1
        seen_urls.add(source.get("url"))
unpublished = sum(
    dish.get("status") == "published"
    and any(
        source.get("reviewStatus") != "approved" or not source.get("license")
        for source in dish.get("sources", [])
    )
    for dish in dishes
)
print(f"count={len(dishes)} invalid={invalid} unpublished_without_license={unpublished}")
if not 300 <= len(dishes) <= 500 or len(set(slugs)) != len(slugs) or invalid or unpublished:
    raise SystemExit(1)
