"""Compare the two H3 workflows: ours (i2v) and the official r2v template."""
import json
import sys
from pathlib import Path


def show(path, label, limit=40):
    print(f"=== {label}: {path}")
    d = json.load(open(path, encoding="utf-8-sig"))
    nodes = d.get("nodes", d)
    if isinstance(nodes, dict):
        for nid, n in nodes.items():
            if not isinstance(n, dict):
                continue
            ct = n.get("class_type", "")
            ins = json.dumps(n.get("inputs", {}), ensure_ascii=False)
            print(f"{nid:>4} {ct:<32} {ins[:150]}")
    else:
        for n in nodes:
            ct = n.get("type", "")
            print(f"{n.get('id'):>4} {ct:<32} {str(n.get('widgets_values'))[:130]}")
    print()


for arg in sys.argv[1:]:
    show(arg, Path(arg).name)
