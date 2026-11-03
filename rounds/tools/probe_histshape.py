"""The shape of what the card keeps, rather than a guess at it.

The history endpoint is read three different ways and each gave the wrong
answer: one list, one map, and a node count of one when there are twenty-odd.
The structure is printed as it arrives so the reader below is written
against the fact instead of against a supposition.
"""
import json
import urllib.request

HOST = "http://192.168.31.7:8188"
out = []

with urllib.request.urlopen(HOST + "/history?max_items=2", timeout=40) as r:
    hist = json.loads(r.read())

out.append(f"顶层类型 {type(hist).__name__}  条数 {len(hist)}")
first_key = next(iter(hist))
rec = hist[first_key]
out.append(f"记录键: {first_key}")
out.append(f"记录字段: {sorted(rec)}")

p = rec.get("prompt")
out.append(f"prompt 类型: {type(p).__name__}")
if isinstance(p, list):
    out.append(f"  长度 {len(p)}")
    for i, item in enumerate(p[:3]):
        out.append(f"  [{i}] {type(item).__name__}: "
                   f"{json.dumps(item, ensure_ascii=False)[:300]}")
elif isinstance(p, dict):
    out.append(f"  键数 {len(p)}  键: {sorted(p)[:8]}")
    k = next(iter(p))
    out.append(f"  样本 {k}: {json.dumps(p[k], ensure_ascii=False)[:400]}")

# outputs is where the file names live
o = rec.get("outputs")
out.append("")
out.append(f"outputs 类型: {type(o).__name__}")
if isinstance(o, dict):
    for k, v in o.items():
        out.append(f"  节点 {k}: {json.dumps(v, ensure_ascii=False)[:300]}")

# status
s = rec.get("status") or {}
out.append("")
out.append(f"status: {json.dumps(s, ensure_ascii=False)[:400]}")

# the actual submitted graph, if the card exposes it
out.append("")
out.append("=== 找提交的图 ===")
for field in ("prompt", "graph", "workflow"):
    v = rec.get(field)
    out.append(f"  {field}: {type(v).__name__} "
               f"{'len=' + str(len(v)) if hasattr(v, '__len__') else ''}")

Path = __import__("pathlib").Path
Path(r"C:\Users\David\AppData\Local\Temp\opencode\histshape.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
