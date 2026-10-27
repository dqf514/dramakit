import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"E:\dramakit\config\comfyui\i2v_minimax_h3.json"
d = json.load(open(path, encoding="utf-8"))
if "nodes" in d:
    nodes = d["nodes"]
else:
    nodes = list(d.values())
print("节点数:", len(nodes))
for n in nodes:
    if not isinstance(n, dict):
        continue
    t = n.get("type") or n.get("class_type")
    ttl = n.get("title") or n.get("name") or ""
    ins = n.get("inputs")
    if isinstance(ins, list):
        names = [i.get("name") for i in ins if isinstance(i, dict)]
    else:
        names = list(ins or [])
    print(f"  {n.get('id')}: {t}  {ttl[:36]}  inputs={names}")
