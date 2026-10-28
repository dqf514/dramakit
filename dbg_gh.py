import json
import sys

for path in sys.argv[1:]:
    d = json.load(open(path, encoding="utf-8-sig"))
    for r in d.get("items", []):
        stars = r.get("stargazers_count", 0)
        name = r.get("full_name", "")
        desc = (r.get("description") or "")[:62]
        print(f"{stars:>6}  {name:<45} {desc}")
