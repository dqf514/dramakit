import json
import sys

for path in sys.argv[1:]:
    d = json.load(open(path, encoding="utf-8-sig"))
    items = d if isinstance(d, list) else d.get("items", [])
    for r in items:
        name = r.get("modelId") or r.get("full_name") or r.get("id") or "?"
        print(name)
