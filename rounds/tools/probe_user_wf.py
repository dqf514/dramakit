"""What the short-drama workflow takes, and what already has to be filled.

The user's workflow for the 3090 is a different file from the one the
config points at, and the pipeline fills a workflow by node id: prompt,
length, resolution, reference pictures, audio. Before swapping it in, the
nodes that carry those values have to be found, and the ones the pipeline
already knows how to set have to be named the way it names them.
"""
import json
from pathlib import Path

SRC = Path(r"D:\Downloads\短剧专用.json")
out = []

raw = SRC.read_text(encoding="utf-8")
out.append(f"文件 {len(raw):,} 字节")
data = json.loads(raw)

# which shape is it: API format {id: node} or UI format {nodes: [...]}
if isinstance(data, dict) and "nodes" in data:
    out.append("格式: UI 导出（有 nodes 数组）")
    nodes = {str(n.get("id")): n for n in data["nodes"]}
elif isinstance(data, dict):
    out.append(f"格式: API（{{id: node}}，{len(data)} 个节点）")
    nodes = {str(k): v for k, v in data.items()}
else:
    out.append("格式: 未知")
    nodes = {}

out.append("")
out.append("=== 全部节点类型 ===")
for nid in sorted(nodes, key=lambda x: int(x) if str(x).isdigit() else 0):
    n = nodes[nid]
    ct = n.get("class_type", n.get("type", "?"))
    title = ""
    if isinstance(n, dict):
        meta = n.get("_meta") or {}
        title = meta.get("title", "") or n.get("title", "")
    inputs = list((n.get("inputs") or {}).keys()) if isinstance(n.get("inputs"), dict) else []
    out.append(f"  #{nid:<6} {ct:<36} {title}")
    if inputs:
        out.append(f"          输入: {', '.join(inputs)}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\wf.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
