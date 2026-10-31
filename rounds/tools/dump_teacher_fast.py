"""Every node in the teacher's fast workflows."""
import json
from pathlib import Path

folder = Path(r"E:\\dramakit\\rounds\\teacher_h3")
for f in sorted(folder.glob("*.json")):
    if "文生视频" not in f.name and "视频放大" not in f.name:
        continue
    d = json.loads(f.read_text(encoding="utf-8"))
    nodes = d.get("nodes") or []
    print("=" * 72)
    print(f.name, f"({len(nodes)} 节点)")
    for n in nodes:
        t = str(n.get("type", ""))
        w = n.get("widgets_values")
        bits = ""
        if isinstance(w, dict):
            bits = " ".join(f"{k}={v}" for k, v in list(w.items())[:8])
        elif isinstance(w, list):
            bits = " ".join(str(x)[:30] for x in w[:8])
        if n.get("title"):
            bits += f"  [{n.get('title')}]"
        print(f"  {n.get('id'):>5} {t:<32} {bits[:120]}")
