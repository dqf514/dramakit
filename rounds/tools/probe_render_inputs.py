"""Find the recordings, and what one shot would actually be given.

The pipeline hands the card three things: a first frame, the character
sheets, and the voice the speaker was recorded with. This reads them out of
the project the way the pipeline does, so the render that follows is the
render the pipeline would ask for - not a stand-in.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
root = Path(r"E:\dramakit\projects")
proj = next((d for d in root.iterdir()
             if d.is_dir() and (d / "project.json").exists()), None)
out.append(f"项目: {proj.name}")

# --- the recordings ----------------------------------------------------
out.append("")
out.append("=== 全项目里的音频文件 ===")
auds = [f for f in proj.rglob("*") if f.is_file()
        and f.suffix.lower() in (".mp3", ".wav", ".m4a", ".flac", ".ogg")]
out.append(f"  共 {len(auds)} 个")
for f in auds[:20]:
    out.append(f"    {f.relative_to(proj)}  {f.stat().st_size/1024:.0f} KB")
if not auds:
    out.append("    （一个都没有）")

# --- characters, and what each one carries -----------------------------
out.append("")
out.append("=== 角色目录里有什么 ===")
ch = proj / "characters"
for d in sorted(ch.iterdir())[:4]:
    if not d.is_dir():
        continue
    files = {f.name: f.stat().st_size for f in d.rglob("*") if f.is_file()}
    out.append(f"  {d.name}:")
    for name, size in sorted(files.items()):
        out.append(f"      {name:22} {size/1024:8.0f} KB")

# --- project.json: the characters the pipeline knows about -------------
out.append("")
out.append("=== project.json 里的角色 ===")
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
chars = raw.get("characters") or []
out.append(f"  {len(chars)} 个")
for c in chars[:5]:
    if isinstance(c, dict):
        out.append(f"    name={c.get('name')!r} "
                   f"voice_ref={c.get('voice_ref')!r} "
                   f"ref_images={c.get('ref_images')!r}")

# --- the shots that already have a video, for a prompt to copy ---------
out.append("")
out.append("=== 已有视频的镜头（可借提示词）===")
vids = sorted((proj / "video").glob("*.mp4"))
for v in vids:
    out.append(f"  {v.name}  {v.stat().st_size/1024:.0f} KB")

# find a shot record with a video_prompt
store = proj / "episodes"
out.append("")
out.append("=== episodes 目录 ===")
if store.exists():
    fs = [f for f in store.rglob("*") if f.is_file()]
    out.append(f"  {len(fs)} 个文件")
    for f in fs[:10]:
        out.append(f"    {f.relative_to(proj)}  {f.stat().st_size/1024:.0f} KB")
else:
    out.append("  不存在")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\render_inputs.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
