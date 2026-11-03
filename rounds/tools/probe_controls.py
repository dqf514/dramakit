"""What each control node in the workflow is called, and what it holds.

The pipeline writes to a workflow by node id and field name, and this
workflow keeps its prompt, duration and resolution in separate control
nodes rather than on the model node. Before the mapping can be written,
each one's field has to be named as the file names it.
"""
import json
from pathlib import Path

data = json.loads(Path(r"D:\Downloads\短剧专用.json").read_text(encoding="utf-8"))
nodes = {str(n.get("id")): n for n in data.get("nodes", [])}

out = []
want = ["136", "138", "132", "115", "137", "139", "129", "130", "127",
        "128", "145", "143", "144", "146", "121", "122", "92", "131", "151",
        "119", "120", "141", "142"]

for nid in want:
    n = nodes.get(nid)
    if not n:
        out.append(f"  #{nid}: 不存在")
        continue
    ct = n.get("type", "?")
    title = (n.get("title") or (n.get("properties") or {}).get("Node name for S&R") or "")
    wvals = n.get("widgets_values")
    ins = n.get("inputs") or []
    conn = [i.get("name") for i in ins if isinstance(i, dict) and "link" in i]
    out.append(f"  #{nid:<5} {ct:<32} {title}")
    out.append(f"        widgets_values: {json.dumps(wvals, ensure_ascii=False)[:150]}")
    if conn:
        out.append(f"        连接型输入: {conn}")

out.append("")
out.append("=== #136 的全部 inputs ===")
n = nodes.get("136") or {}
for i in (n.get("inputs") or []):
    out.append(f"  {json.dumps(i, ensure_ascii=False)[:120]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\controls.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
