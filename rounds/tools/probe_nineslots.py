"""Eight pictures into nine slots, and what is left over.

A shot with two characters sends eight pictures - the frame it continues
from, where the last one ended, a face and a turnaround for each person,
the room - and the workflow this replaced had nine slots for them. The new
file wired two, so the zip that pairs pictures with slots stopped after
the second and the sheets and the room were dropped without a word: the
job ran, the pictures simply were not in it.

So the real plan is fed through the real filling code, and the graph is
read back: how many slots took a picture, which they were, and whether
the ones with no picture came out of the job rather than going to the
card with the file's own placeholder in them.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.providers.comfyui import ComfyUIClient  # noqa: E402

out = []
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

# --- what picture_plan would hand over for a two-character shot ---------
chars = [c for c in raw.get("characters", []) if isinstance(c, dict) and c.get("ref_images")]
who = [c for c in chars if c.get("voice_ref")]
c1, c2 = who[0], who[1]

first_frames = sorted((proj / "images").glob("*.png"))
prev_videos = sorted((proj / "video").glob("*.mp4"))
rooms = [f for f in (proj / "locations").rglob("*")
         if f.is_file() and f.suffix.lower() in (".png", ".jpg")] \
    if (proj / "locations").exists() else []

# in picture_plan's order: frame, handoff, face, views, face, views, room
plan = [str(first_frames[0])] if first_frames else []
if prev_videos:
    plan.append(str(prev_videos[-1]))
for c in (c1, c2):
    refs = [str(proj / p) for p in c["ref_images"]]
    face = next((p for p in refs if "face" in p and Path(p).exists()), None)
    views = next((p for p in refs if "sheet" in p and Path(p).exists()), None)
    if face:
        plan.append(face)
    if views:
        plan.append(views)
if rooms:
    plan.append(str(rooms[0]))

out.append(f"=== picture_plan 的产出（两个角色）{len(plan)} 张 ===")
for i, p in enumerate(plan):
    out.append(f"  [{i}] {Path(p).name}  存在={Path(p).exists()}")

# --- feed it through the real filling code ------------------------------
cfg = Config.load(Config.discover())
client = ComfyUIClient(cfg.comfyui, root=Path(r"E:\dramakit"))
graph = copy.deepcopy(client._load_workflow(cfg.comfyui.i2v_workflow, "i2v"))

from dramakit.providers.comfyui import _ref_slots, _put_ref_slots  # noqa: E402

ref_node = None
for node in graph.values():
    if "ReferenceToVideo" in str(node.get("class_type", "")):
        ref_node = node
        break

slots_map, shape = _ref_slots(ref_node, "ref_images")
out.append("")
out.append(f"=== 工作流的 ref_image 槽：{len(slots_map)} 个（shape={shape}）===")
slots = []
for slot, link in sorted(slots_map.items()):
    if isinstance(link, list) and link:
        slots.append((str(link[0]), slot))
        out.append(f"  {slot} -> #{link[0]}")

# the loop generate_video runs
out.append("")
out.append("=== 逐张填充 ===")
used = set()
for (load_id, slot), path in zip(slots, plan):
    ok_node = load_id in graph
    ok_file = Path(path).exists()
    mark = "✓" if (ok_node and ok_file) else "跳过"
    out.append(f"  {Path(path).name:24} -> #{load_id} ({slot})  {mark}")
    if not ok_node or not ok_file:
        continue
    graph[load_id].setdefault("inputs", {})["image"] = f"uploaded_{Path(path).name}"
    used.add(slot)

dropped_pictures = plan[len(slots):]
out.append("")
out.append(f"  填了 {len(used)}/{len(slots)} 槽")
if dropped_pictures:
    out.append(f"  **溢出被丢弃 {len(dropped_pictures)} 张**:")
    for p in dropped_pictures:
        out.append(f"      {Path(p).name}")

# the guard: slots with no picture come out of the job
imgs, _s = _ref_slots(ref_node, "ref_images")
for slot in list(imgs):
    if slot not in used:
        imgs.pop(slot)
_put_ref_slots(ref_node, "ref_images", imgs, shape)

out.append("")
out.append("=== 提交给卡的 ref_images ===")
final, _ = _ref_slots(ref_node, "ref_images")
for slot, link in sorted(final.items()):
    nid = str(link[0])
    n = graph.get(nid) or {}
    img = (n.get("inputs") or {}).get("image")
    out.append(f"  {slot} -> #{nid} image={img!r}")

# would the card accept it? every LoadImage still in the job has a file
out.append("")
problems = []
for slot, link in final.items():
    nid = str(link[0])
    n = graph.get(nid) or {}
    if n.get("class_type") == "LoadImage" and not (n.get("inputs") or {}).get("image"):
        problems.append(f"#{nid} 空 image（会被卡拒）")
# and any LoadImage left in the graph but not wired in is harmless, since
# an unwired node is not executed - but say so
orphans = [k for k, n in graph.items()
           if n.get("class_type") == "LoadImage"
           and k not in {str(l[0]) for l in final.values()}]
out.append(f"  溢出的 LoadImage（未接线，不执行）: {orphans}")
if problems:
    for p in problems:
        out.append(f"  **{p}**")
else:
    out.append("  **无问题**：所有接线的 LoadImage 都有图")

# --- the audio slot survives all this ----------------------------------
auds, ashape = _ref_slots(ref_node, "ref_audios")
out.append("")
out.append(f"=== 音频槽（shape={ashape}）===")
out.append(f"  {auds}")
for slot, link in auds.items():
    nid = str(link[0])
    out.append(f"  #{nid} {graph.get(nid, {}).get('class_type')} "
               f"存在={nid in graph}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\nineslots.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
