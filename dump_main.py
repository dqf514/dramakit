import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"E:\dramakit\_klein_mi2i.json"
w = json.load(open(path, encoding="utf-8"))
print("=== 顶层节点 ===")
for n in w["nodes"]:
    nid = n.get("id")
    ct = n.get("type")
    wv = json.dumps(n.get("widgets_values"), ensure_ascii=False)
    if len(wv) > 110:
        wv = wv[:110] + "..."
    ins = ", ".join(f"{i.get('name')}<-{i.get('link')}" for i in (n.get("inputs") or []))
    print(f"{nid:>4} {ct:<34} in[{ins}]  {wv}")

print("\n=== links ===")
for l in w.get("links") or []:
    # [id, origin_node, origin_slot, target_node, target_slot, type]
    print(f"  {l[0]:>4}: {l[1]}.{l[2]} -> {l[3]}.{l[4]}  ({l[5]})")
