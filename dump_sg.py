import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"E:\dramakit\_klein_t2i.json"
w = json.load(open(path, encoding="utf-8"))
print("top keys:", list(w.keys()))
defs = w.get("definitions") or {}
print("definitions keys:", list(defs.keys()))
for sg in defs.get("subgraphs", []):
    print("\n" + "=" * 70)
    print("SUBGRAPH", sg.get("id"), "|", sg.get("name"))
    print("  keys:", list(sg.keys()))
    ins = sg.get("inputs") or []
    outs = sg.get("outputs") or []
    print("  subgraph inputs:", [(i.get("name"), i.get("type")) for i in ins])
    print("  subgraph outputs:", [(o.get("name"), o.get("type")) for o in outs])
    nodes = sg.get("nodes") or []
    print("  inner nodes:", len(nodes))
    for n in nodes:
        wv = json.dumps(n.get("widgets_values"), ensure_ascii=False)
        if len(wv) > 220:
            wv = wv[:220] + "..."
        print(f"    {n.get('id'):>4} {n.get('type'):<28} {wv}")
        for i in n.get("inputs") or []:
            if i.get("widget") is None:
                print(f"         link-in: {i.get('name')} ({i.get('type')}) <- link {i.get('link')}")
        for o in n.get("outputs") or []:
            print(f"         out: {o.get('name')} ({o.get('type')}) -> links {o.get('links')}")
