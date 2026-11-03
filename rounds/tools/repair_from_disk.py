"""Put back what the re-analysis dropped, and remove the season it invented.

The analysis re-ran and the merge rebuilt every character from scratch,
carrying voice and role and nothing else - so the recordings made at 定妆
and the pictures already drawn fell out of the model while both stayed on
disk. A later stage would see characters with no pictures and draw them
again, which is exactly what happened, into a folder for a season that
was never asked for.

Both are restored from the files that are there: the sample beside each
character's pictures, and the pictures themselves. The season that the
wrong choice created is removed, along with the pictures it drew - they
are duplicates of ones that already exist.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.project import ProjectStore, slugify

root = Path(r"E:\dramakit\projects\魔兽世界")
store = ProjectStore.open(root)
proj = store.load()
cfg = Config.load(Config.discover())

out = []

# ---------------------------------------------- 1. the season that was not
spurious = [s for s in (proj.seasons or []) if s.index != 1]
for s in spurious:
    out.append(f"删除第 {s.index} 季（chapters={s.chapters}）")
    # and the pictures it drew into a per-season folder
    cdir = root / "characters"
    if cdir.exists():
        for sub in cdir.rglob(f"s{s.index}"):
            if sub.is_dir():
                n = len(list(sub.glob("*")))
                for f in sub.glob("*"):
                    f.unlink()
                sub.rmdir()
                out.append(f"  清空 {sub.relative_to(root)}（{n} 张重复图）")
proj.seasons = [s for s in (proj.seasons or []) if s.index == 1]

# the season it was on is season 1, whatever the analysis thought
season1 = proj.season(1)
if season1 is not None:
    # the stages the project-level status says are done belong to it too
    for k, v in (proj.stage_status or {}).items():
        if k in ("analyze", "character", "segment", "script", "storyboard"):
            season1.stage_status[k] = v
    out.append("第 1 季阶段: " + json.dumps(
        {k: str(v.value if hasattr(v, "value") else v)
         for k, v in season1.stage_status.items()}, ensure_ascii=False))

# ------------------------------------------------ 2. restore from disk ----
restored_v = restored_r = 0
for c in proj.characters:
    folder = root / "characters" / slugify(c.name)
    if not folder.exists():
        out.append(f"  {c.name}: 磁盘上没有目录（跳过）")
        continue
    voice = sorted(folder.glob("voice.*"))
    if voice:
        c.voice_ref = store.rel(voice[0])
        restored_v += 1
    pics = sorted(p for p in folder.glob("*")
                  if p.suffix.lower() in (".png", ".jpg") and p.is_file())
    if pics:
        rels = [store.rel(p) for p in pics]
        c.ref_images = rels
        sheet = [r for r in rels if "sheet" in r]
        c.ref_sheet = sheet[0] if sheet else (rels[0] if rels else "")
        restored_r += 1

out.append(f"恢复声音 {restored_v} 个，恢复参考图 {restored_r} 个角色")
proj.stage_status["character"] = "interrupted"   # it did not finish
store.save(proj)

out.append("")
out.append("=== 修复后 ===")
d = json.loads((root / "project.json").read_text(encoding="utf-8"))
for c in d.get("characters", []):
    out.append(f"  {c.get('name'):<20} voice={bool(c.get('voice_ref'))} "
               f"图={len(c.get('ref_images') or [])} "
               f"锚={'有' if c.get('anchor_prompt') else '无'}")
out.append(f"  季: {[s.get('index') for s in d.get('seasons', [])]}")
out.append("  stage: " + json.dumps(d.get("stage_status", {}), ensure_ascii=False))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\repair.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
