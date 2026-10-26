import json
import sys

for n in ("01", "02", "05", "07"):
    p = rf"E:\dramakit\rounds\轮次{n}_{n}.qa.json"
    try:
        d = json.load(open(p, encoding="utf-8"))
    except FileNotFoundError:
        continue
    e = d["episodes"][0]
    s = e.get("sync") or {}
    st = e.get("story") or {}
    print(f"第{n}轮: 台词不在切点上 {s.get('off_cut')} 句, 离屏 {st.get('mismatched')} 句")
    for r in (s.get("rows") or [])[:5]:
        print(f"    「{r['text']}」 迟 {r['drift']}s")
