import json
import sys

for n in ("01", "02", "03"):
    p = rf"E:\dramakit\rounds\轮次{n}_{n}.qa.json"
    d = json.load(open(p, encoding="utf-8"))
    v = d["episodes"][0]["voice"]
    print(f"轮次{n}: {v['lines']} 句配音")
    for who, s in (v.get("voices") or {}).items():
        print(f"   {who:12s} 基频 {s['pitch']:6.1f}Hz  过零率 {s['zcr']:7.1f}  "
              f"{s['lines']} 句")
