"""What the file the user just handed over contains.

It arrived in API form this time - a map of id to node rather than the
nodes-and-links export the converter was written for - so the conversion
is a no-op and whatever is in the file is what will run. Before it is
swapped in, the things that were wrong with the previous one have to be
checked here: the switch and its step count, the attention patch, the
reference slots, and the weights each loader names.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

NEW = Path(r"D:\Downloads\短剧专用.json")
OURS = Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
out = []

raw = json.loads(NEW.read_text(encoding="utf-8"))
out.append(f"=== 用户给的文件（{len(raw)} 节点，{NEW.stat().st_size} 字节）===")
out.append(f"  格式: {'API' if all(isinstance(v, dict) and 'class_type' in v for v in raw.values()) else 'UI'}")

for nid, n in sorted(raw.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
    ct = n.get("class_type", "?")
    ins = n.get("inputs") or {}
    out.append(f"  #{nid:<5} {ct}")
    if ins:
        out.append(f"        {json.dumps(ins, ensure_ascii=False)[:260]}")

# --- the four things that were wrong before ----------------------------
out.append("")
out.append("=== 关键项 ===")
for want in ("PrimitiveBoolean", "PrimitiveInt", "LoraLoaderModelOnly",
             "PathchSageAttentionKJ", "BasicScheduler", "KSamplerSelect",
             "MiniMaxH3ReferenceToVideo", "LoadAudio", "LoadImage",
             "UNETLoader", "CLIPLoader"):
    hits = [(nid, n) for nid, n in raw.items()
            if n.get("class_type") == want]
    out.append(f"  {want}: {len(hits)} 个 " +
               (", ".join(f"#{h[0]}" for h in hits) if hits else ""))

# the switch and what it selects
out.append("")
out.append("=== 开关 ===")
for nid, n in raw.items():
    if n.get("class_type") == "PrimitiveBoolean":
        out.append(f"  #{nid} = {(n.get('inputs') or {}).get('value')}")
    if n.get("class_type") == "PrimitiveInt":
        out.append(f"  #{nid} 步数候选 = {(n.get('inputs') or {}).get('value')}")
    if n.get("class_type") == "ComfySwitchNode":
        out.append(f"  #{nid} 开关: {json.dumps(n.get('inputs'), ensure_ascii=False)}")

# the model path from the attention patch back to a loader
out.append("")
out.append("=== 模型链路（从 SageAttention 往回追）===")
by_id = raw


def back(nid, depth=0, seen=None):
    seen = seen or set()
    if nid in seen or depth > 6:
        return
    seen.add(nid)
    n = by_id.get(nid)
    if not n:
        return
    ct = n.get("class_type", "?")
    out.append("    " + "  " * depth + f"#{nid} {ct}")
    for k, v in (n.get("inputs") or {}).items():
        if k == "model" and isinstance(v, list):
            back(str(v[0]), depth + 1, seen)


sage = next((nid for nid, n in raw.items()
             if "SageAttention" in str(n.get("class_type", ""))), None)
if sage:
    back(sage)
else:
    out.append("  **没有 SageAttention 节点**")

# reference slots
out.append("")
out.append("=== 参考槽 ===")
for nid, n in raw.items():
    if "ReferenceToVideo" in str(n.get("class_type", "")):
        ins = n.get("inputs") or {}
        imgs = sorted(k for k in ins if k.startswith("ref_images."))
        auds = sorted(k for k in ins if k.startswith("ref_audios."))
        vids = sorted(k for k in ins if k.startswith("ref_videos."))
        out.append(f"  #{nid} 图 {len(imgs)} 音 {len(auds)} 视频 {len(vids)}")
        out.append(f"      {imgs} {auds} {vids}")

# --- against ours -------------------------------------------------------
out.append("")
out.append("=== 与我们当前的对比 ===")
ours = json.loads(OURS.read_text(encoding="utf-8"))
out.append(f"  用户文件 {len(raw)} 节点 / 我们 {len(ours)} 节点")
only_new = set(raw) - set(ours)
only_ours = set(ours) - set(raw)
out.append(f"  只在用户文件: {sorted(only_new, key=lambda x: int(x) if x.isdigit() else 0)}")
out.append(f"  只在我们文件: {sorted(only_ours, key=lambda x: int(x) if x.isdigit() else 0)}")
diff = []
for nid in set(raw) & set(ours):
    a, b = raw[nid], ours[nid]
    if a.get("class_type") != b.get("class_type"):
        diff.append(f"  #{nid} 类型不同: {a.get('class_type')} vs {b.get('class_type')}")
    elif (a.get("inputs") or {}) != (b.get("inputs") or {}):
        diff.append(f"  #{nid} 输入不同:")
        ai, bi = a.get("inputs") or {}, b.get("inputs") or {}
        for k in sorted(set(ai) | set(bi)):
            if ai.get(k) != bi.get(k):
                out.append(f"      {k}: 用户={json.dumps(ai.get(k), ensure_ascii=False)[:80]}"
                           f"  我们={json.dumps(bi.get(k), ensure_ascii=False)[:80]}")
if not diff:
    out.append("  共同节点的输入完全相同")
else:
    out.extend(diff)

Path(r"C:\Users\David\AppData\Local\Temp\opencode\newfile.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
