"""What the reference injection actually leaves in the graph.

The card refused the job because the third picture slot was empty, and the
code that fills those slots skips a picture whose file it cannot find -
silently, so the slot stays as the file shipped it and the card refuses
the whole job. Whether the skip is the cause is not something to argue
from: the graph is rebuilt here exactly as generate_video rebuilds it, and
read back.

The card is not asked to run anything; only the graph is inspected.
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
chars = raw.get("characters") or []
who = next(c for c in chars if isinstance(c, dict) and c.get("voice_ref"))

refs = [proj / p for p in (who.get("ref_images") or [])]
out.append(f"角色 {who.get('name')!r} 的 ref_images 原始列表:")
for p in refs:
    out.append(f"    {'存在' if p.exists() else '**不存在**'}  {p}")

refs_ok = [p for p in refs if p.exists()]
pictures = [str(p) for p in refs_ok[:3]]
out.append("")
out.append(f"过滤后 {len(refs_ok)} 张，取前 3 张送入:")
for p in pictures:
    out.append(f"    {Path(p).name}  存在={Path(p).exists()}")

cfg = Config.load(Config.discover())
client = ComfyUIClient(cfg.comfyui, root=Path(r"E:\dramakit"))
graph = copy.deepcopy(client._load_workflow(cfg.comfyui.i2v_workflow, "i2v"))

# --- exactly what generate_video does to the picture slots -------------
out.append("")
out.append("=== 注入前的 ref_images 槽 ===")
ref_node = None
for nid, node in graph.items():
    if "ReferenceToVideo" in str(node.get("class_type", "")):
        ref_node = node
        out.append(f"  模型节点 #{nid}")
        for slot, link in sorted(
                (node.get("inputs", {}).get("ref_images") or {}).items()):
            out.append(f"    {slot} -> {link}")
        break

slots: list[tuple[str, str]] = []
for slot, link in sorted((ref_node.get("inputs", {}).get("ref_images") or {}).items()):
    if isinstance(link, list) and link:
        slots.append((str(link[0]), slot))
out.append("")
out.append(f"  代码读到的 slots = {slots}")

out.append("")
out.append("=== 逐张尝试填充 ===")
used: set[str] = set()
for (load_id, slot), path in zip(slots, pictures):
    exists = Path(path).exists()
    in_graph = load_id in graph
    out.append(f"  {Path(path).name:22} -> #{load_id} ({slot})  "
               f"节点在图里={in_graph} 文件存在={exists}")
    if not in_graph or not exists:
        out.append("      **跳过**")
        continue
    graph[load_id].setdefault("inputs", {})["image"] = f"uploaded_{Path(path).name}"
    used.add(slot)
out.append(f"  used = {used}")

out.append("")
out.append("=== 注入后的 ref_images 槽 ===")
imgs = dict(ref_node.get("inputs", {}).get("ref_images") or {})
for slot in list(imgs):
    if slot not in used:
        out.append(f"  **删掉** {slot} -> {imgs[slot]}")
        imgs.pop(slot)
ref_node.setdefault("inputs", {})["ref_images"] = imgs
for slot, link in sorted(imgs.items()):
    out.append(f"  保留 {slot} -> {link}")

out.append("")
out.append("=== 三个 LoadImage 节点最终状态 ===")
for nid in ("137", "139", "162"):
    n = graph.get(nid)
    if not n:
        out.append(f"  #{nid}: **不在图里**")
        continue
    out.append(f"  #{nid} {n.get('class_type')} inputs={json.dumps(n.get('inputs'), ensure_ascii=False)}")

out.append("")
out.append("=== 卡上会不会接受 ===")
for nid in ("137", "139", "162"):
    n = graph.get(nid) or {}
    if n.get("class_type") == "LoadImage" and not (n.get("inputs") or {}).get("image"):
        out.append(f"  #{nid} 空 image -> 会被拒")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\inject.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
