"""What survived the re-analysis, and what the merge threw away.

The analysis re-ran - it has no skip guard - and _merge_characters builds
new characters carrying only a few fields, so the voice samples recorded
at 定妆 and the reference pictures already drawn were dropped from the
model even though both are still on disk. This stops the run and lists
what is actually there, so the repair points at files that exist rather
than at regenerating them.
"""
import json
import time
from pathlib import Path

root = Path(r"E:\dramakit\projects\魔兽世界")
out = []

# wait for the stop to land
for _ in range(30):
    time.sleep(3)
    d = json.loads((root / "project.json").read_text(encoding="utf-8"))
    if d.get("stage_status", {}).get("character") != "running":
        break

d = json.loads((root / "project.json").read_text(encoding="utf-8"))
out.append("阶段: " + json.dumps(d.get("stage_status", {}), ensure_ascii=False))
out.append("")
out.append("=== 模型里的角色字段 ===")
for c in d.get("characters", []):
    out.append(f"  {c.get('name'):<22} voice_ref={c.get('voice_ref') or '(空)':<34} "
               f"ref_images={len(c.get('ref_images') or [])} "
               f"anchor={'有' if c.get('anchor_prompt') else '无'}")

out.append("")
out.append("=== 磁盘上真正有的 ===")
cdir = root / "characters"
if cdir.exists():
    voices = sorted(cdir.rglob("voice.*"))
    pics = [f for f in cdir.rglob("*") if f.suffix.lower() in (".png", ".jpg")]
    out.append(f"  声音样本 {len(voices)} 个")
    out.append(f"  参考图   {len(pics)} 张")
    by_dir = {}
    for f in pics:
        by_dir.setdefault(f.parent.name, []).append(f.name)
    for k, v in sorted(by_dir.items()):
        out.append(f"    {k}: {sorted(v)}")

out.append("")
out.append("=== 项目里的集/镜头 ===")
eps = d.get("episodes", [])
imgs = vids = prompts = 0
for e in eps:
    for sc in e.get("scenes", []):
        for sh in sc.get("shots", []):
            prompts += 1 if sh.get("prompt") else 0
            imgs += 1 if sh.get("image_path") else 0
            vids += 1 if sh.get("video_path") else 0
out.append(f"  {len(eps)} 集, {prompts} 镜有提示词, {imgs} 张首帧, {vids} 段视频")

out.append("")
out.append("=== 季记录 ===")
for s in d.get("seasons", []):
    out.append(f"  第{s.get('index')}季 chapters={s.get('chapters')} "
               f"stages={json.dumps(s.get('stage_status', {}), ensure_ascii=False)}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\survey.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
