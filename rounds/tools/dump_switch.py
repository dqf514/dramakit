"""What does the switch in the teacher's fast workflow control?"""
import json
from pathlib import Path

folder = Path(r"E:\\dramakit\\rounds\\teacher_h3")
for fname in ("H3-文生视频-高速高质.json", "H3-文生视频-高清成品.json",
              "H3-文生视频-快速预览.json"):
    f = folder / fname
    if not f.exists():
        continue
    d = json.loads(f.read_text(encoding="utf-8"))
    for n in d.get("nodes") or []:
        if n.get("id") != 140:
            continue
        w = n.get("widgets_values") or []
        print("=" * 72)
        print(fname)
        print("  子图节点的 widget 值:")
        for i, v in enumerate(w):
            print(f"    [{i}] {str(v)[:90]}")
        print("  子图的输入:")
        for inp in (n.get("inputs") or []):
            print(f"    {inp.get('name')}: {str(inp.get('type'))} "
                  f"link={inp.get('link')} widget={inp.get('widget',{}).get('name')}")
        # the subgraph's own nodes and their links
        defs = d.get("definitions") or {}
        subs = defs.get("subgraphs") if isinstance(defs, dict) else None
        for s in subs or []:
            print("  --- 子图内部 ---")
            for sn in s.get("nodes") or []:
                st = str(sn.get("type", ""))
                if st in ("Note", "MarkdownNote", "PrimitiveFloat",
                          "PrimitiveInt", "PrimitiveBoolean", "ComfyMathExpression",
                          "ComfySwitchNode", "LoraLoaderModelOnly",
                          "BasicScheduler", "KSamplerSelect", "RandomNoise",
                          "CreateVideo", "UNETLoader"):
                    sw = sn.get("widgets_values")
                    sv = sw if isinstance(sw, dict) else sw
                    print(f"    {sn.get('id'):>4} {st:<26} {str(sv)[:110]}")
                    for inp in (sn.get("inputs") or []):
                        if inp.get("link") is not None:
                            print(f"          in {inp.get('name')} <- link {inp.get('link')}")
