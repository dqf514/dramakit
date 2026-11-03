"""What the switches are set to, and what the video slot needs.

The sampler takes its model from a node wired straight to the loader, so
the LoRA and its switch sit off the path - the file's own wiring, not a
conversion loss. The switches have values that say which mode the author
ran in, and that decides whether the missing LoRA matters.

The previous clip slot was wired to an image loader. A video input takes
a video, and a type mismatch is rejected at submit time rather than
rendering the wrong thing, so the node that belongs there has to exist on
the card.
"""
import json
from pathlib import Path

ui = json.loads(Path(r"D:\Downloads\短剧专用.json").read_text(encoding="utf-8"))
nodes = {str(n.get("id")): n for n in ui.get("nodes", [])}
links = {str(r[0]): r for r in (ui.get("links") or []) if isinstance(r, list)}
out = []

for nid in ("146", "143", "144", "142", "141"):
    n = nodes.get(nid)
    if not n:
        out.append(f"  #{nid}: 不存在")
        continue
    out.append(f"  #{nid} {n.get('type')}  widgets={json.dumps(n.get('widgets_values'), ensure_ascii=False)[:80]}")
    for inp in n.get("inputs") or []:
        row = links.get(str(inp.get("link"))) if inp.get("link") is not None else None
        out.append(f"      {inp.get('name')} <- " + (f"#{row[1]}" if row else "本地值"))

# what feeds the scheduler's steps
out.append("")
out.append("=== 步数的两个候选 ===")
for nid in ("143", "144"):
    n = nodes.get(nid)
    if n:
        out.append(f"  #{nid} {n.get('type')} widgets={json.dumps(n.get('widgets_values'), ensure_ascii=False)}")

# --- does the card have a video loader? --------------------------------
import sys, urllib.request
sys.path.insert(0, r"E:\dramakit")
out.append("")
for label, host in (("3090", "http://192.168.31.7:8188"),):
    try:
        with urllib.request.urlopen(host + "/object_info", timeout=30) as r:
            info = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        out.append(f"  {label} 读不到: {e}")
        continue
    out.append(f"=== {label} 上的视频/音频加载节点 ===")
    for name in sorted(info):
        low = name.lower()
        if ("loadvideo" in low or "loadaudio" in low or "vhs_" in low
                or low.startswith("load")):
            inp = (info[name].get("input") or {}).get("required") or {}
            out.append(f"  {name}: {list(inp)[:6]}")
    # the switch and sage nodes exist?
    out.append("")
    out.append("  关键节点是否存在:")
    for name in ("ComfySwitchNode", "PathchSageAttentionKJ", "MarkdownNote",
                 "LoraLoaderModelOnly", "MiniMaxH3ReferenceToVideo"):
        out.append(f"    {name}: {'有' if name in info else '**没有**'}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\switchvals.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
