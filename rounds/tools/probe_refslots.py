"""Both shapes read back the same, and each writes back as it came.

The filling code read a nested map and got nothing from a workflow that
keeps its slots as flat keys - the pictures were never uploaded, and the
loaders kept the file's own placeholders. The reader now takes either
shape and returns the shape along with the slots, so the write-back does
not silently convert one workflow into the other.

This reads the two real files - the one that worked and the one that did
not - and prints what each hands over, plus what a round trip leaves.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.providers.comfyui import _ref_slots, _put_ref_slots  # noqa: E402

out = []
for label, rel in (("旧（嵌套）", r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json"),
                   ("新（扁平）", r"E:\dramakit\config\comfyui\i2v_shortdrama.json")):
    p = Path(rel)
    if not p.exists():
        out.append(f"=== {label}: 文件不存在 ===")
        continue
    g = json.loads(p.read_text(encoding="utf-8"))
    node = next(n for n in g.values()
                if "ReferenceToVideo" in str(n.get("class_type", "")))
    out.append(f"=== {label} ({p.name}) ===")
    for key in ("ref_images", "ref_audios"):
        slots, shape = _ref_slots(node, key)
        out.append(f"  {key}: shape={shape}  {len(slots)} 槽")
        for name, link in sorted(slots.items()):
            out.append(f"      {name} -> {link}")
        if not slots:
            out.append("      （空 —— 修之前这里就是这个结果）")
    # round trip: read, drop one slot, write back, read again
    back = copy.deepcopy(node)
    slots, shape = _ref_slots(back, "ref_images")
    if slots:
        first = sorted(slots)[0]
        slots.pop(first)
        _put_ref_slots(back, "ref_images", slots, shape)
        again, shape2 = _ref_slots(back, "ref_images")
        flat_left = [k for k in back["inputs"] if k.startswith("ref_images.")]
        out.append(f"  往返（删 {first} 后写回）: shape={shape2} 剩 {len(again)} 槽 "
                   f"扁平键={flat_left}")
        out.append(f"  写回后的 inputs 形态: "
                   f"{'扁平' if flat_left else '嵌套'}")
    out.append("")

# and what the pipeline now sees for the shipped workflow
out.append("=== 渲染探针会拿到什么 ===")
p = Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
g = json.loads(p.read_text(encoding="utf-8"))
node = next(n for n in g.values()
            if "ReferenceToVideo" in str(n.get("class_type", "")))
slots, shape = _ref_slots(node, "ref_images")
out.append(f"  slots = {sorted(slots)}")
out.append(f"  对应 LoadImage 节点 = {[str(slots[k][0]) for k in sorted(slots)]}")
for k in sorted(slots):
    nid = str(slots[k][0])
    n = g.get(nid, {})
    out.append(f"  #{nid} {n.get('class_type')} 初始 image="
               f"{(n.get('inputs') or {}).get('image')!r}")
auds, _ = _ref_slots(node, "ref_audios")
out.append(f"  ref_audios = {auds}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\refslots.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
