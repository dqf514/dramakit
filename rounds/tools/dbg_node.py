"""Pull the reference-to-video node out of the official template."""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
d = json.load(open(path, encoding="utf-8-sig"))
nodes = d.get("nodes", d)
if isinstance(nodes, dict):
    items = [(k, v) for k, v in nodes.items() if isinstance(v, dict)]
else:
    items = [(n.get("id"), n) for n in nodes]
want = sys.argv[2] if len(sys.argv) > 2 else "Reference"
for nid, n in items:
    ct = n.get("class_type") or n.get("type", "")
    if want.lower() in ct.lower():
        print(f"--- {nid} {ct}")
        print(json.dumps(n.get("inputs", {}), ensure_ascii=False, indent=1)[:1400])
        print()
