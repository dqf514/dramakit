import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"E:\dramakit\_klein_t2i.json"
w = json.load(open(path, encoding="utf-8"))
nodes = w["nodes"] if isinstance(w, dict) and "nodes" in w else w
print("== node count:", len(nodes))
for n in nodes:
    nid = n.get("id")
    ct = n.get("type")
    wv = n.get("widgets_values")
    ins = n.get("inputs") or []
    outs = n.get("outputs") or []
    ins_s = ", ".join(f"{i.get('name')}<-{i.get('link')}" for i in ins)
    outs_s = ", ".join(str(o.get("name")) for o in outs)
    wv_s = json.dumps(wv, ensure_ascii=False)
    if len(wv_s) > 150:
        wv_s = wv_s[:150] + "..."
    print(f"{nid:>4} {ct:<32} widgets={wv_s}")
    print(f"      in[{ins_s}]  out[{outs_s}]")
    if n.get("title"):
        print(f"      title={n['title']}")
