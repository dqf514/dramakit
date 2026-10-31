"""What is different between the teacher's fast and good workflows."""
import json
from pathlib import Path

folder = Path(r"E:\\dramakit\\rounds\\teacher_h3")


def flat(f):
    """Every widget value in the file, by node id."""
    d = json.loads(f.read_text(encoding="utf-8"))
    out = {}

    def walk(nodes, prefix=""):
        for n in nodes or []:
            nid = f"{prefix}{n.get('id')}"
            t = str(n.get("type", ""))
            w = n.get("widgets_values")
            if isinstance(w, dict):
                for k, v in w.items():
                    out[f"{nid}.{t}.{k}"] = v
            elif isinstance(w, list):
                for i, v in enumerate(w):
                    if isinstance(v, (str, int, float, bool)):
                        out[f"{nid}.{t}[{i}]"] = v
            for sub in (n.get("subgraph") or {}).get("nodes", []) or []:
                walk([sub], prefix=f"{nid}.")
    walk(d.get("nodes") or [])
    defs = d.get("definitions") or {}
    subs = defs.get("subgraphs") if isinstance(defs, dict) else None
    for s in subs or []:
        walk(s.get("nodes") or [], prefix="sg.")
    return out


files = {f.name: flat(f) for f in sorted(folder.glob("*文生视频*.json"))}
names = list(files)
base = names[0]
for other in names[1:]:
    print("=" * 72)
    print(f"{base}  vs  {other}")
    a, b = files[base], files[other]
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            print(f"  {k}: {a.get(k)}  ->  {b.get(k)}")
