import json
import sys

name = sys.argv[1]
p = rf"E:\dramakit\rounds\reports\round{name}.qa.json"
d = json.load(open(p, encoding="utf-8"))
e = d["episodes"][0]
st = e.get("story") or {}
print(f"离屏 {st.get('mismatched')} 句")
for r in (st.get("rows") or []):
    print(f"   {r['speaker']} 说「{r['text']}」 镜头 {r['shot']} 里是 {r['on_screen']}")
s = e.get("sync") or {}
print(f"不在切点上 {s.get('off_cut')} 句")
for r in (s.get("rows") or [])[:6]:
    print(f"   「{r['text']}」迟 {r['drift']}s  镜头 {r['shot']}")
