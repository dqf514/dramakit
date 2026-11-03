"""How a multi-widget node records the names of its widgets.

Two nodes came through the conversion with no inputs at all - the
resolution picker and the two picture loaders - because the widget names
were read from a field this export does not carry. The nodes' own input
list does name them, and that is where the values belong.
"""
import json
from pathlib import Path

data = json.loads(Path(r"D:\Downloads\短剧专用.json").read_text(encoding="utf-8"))
nodes = {str(n.get("id")): n for n in data.get("nodes", [])}

out = []
for nid in ("115", "137", "139", "138", "132", "129"):
    n = nodes.get(nid)
    if not n:
        continue
    out.append(f"=== #{nid} {n.get('type')} ===")
    out.append(f"  widgets_values: {json.dumps(n.get('widgets_values'), ensure_ascii=False)}")
    out.append(f"  widgets 字段   : {json.dumps(n.get('widgets'), ensure_ascii=False)}")
    out.append(f"  inputs:")
    for i in (n.get("inputs") or []):
        out.append(f"    {json.dumps(i, ensure_ascii=False)[:150]}")
    out.append("")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\widgets.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
