import json
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/catalog/dishes.json")
dishes = json.loads(path.read_text())
slugs = [dish.get("slug") for dish in dishes]
invalid = sum(not slug or not dish.get("sources") for slug, dish in zip(slugs, dishes))
unpublished = sum(dish.get("status") == "published" and any(not source.get("license") for source in dish.get("sources", [])) for dish in dishes)
print(f"count={len(dishes)} invalid={invalid} unpublished_without_license={unpublished}")
if not 300 <= len(dishes) <= 500 or len(set(slugs)) != len(slugs) or invalid or unpublished:
    raise SystemExit(1)
