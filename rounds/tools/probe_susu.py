"""Where 素素 came from, and what it takes to give her a face.

She is in six shots and nowhere in the cast: the script names her, the
analysis never made an entry, and the gate refuses a shot whose speaker
has no sheets. The question is whether she was dropped, never picked up,
or is somebody under another name - because adding a character with no
pictures costs a round of image generation, and adding one that already
exists costs nothing.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402

cfg = Config.load(Config.discover())
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
ctx = Context(cfg, ProjectStore.open(proj))

out = []
out.append("=== 项目里的角色 ===")
for c in (ctx.project.characters or []):
    out.append(f"  {c.name!r}  refs={len(c.refs() or [])}  "
               f"voice_ref={c.voice_ref!r}")

out.append("")
out.append("=== 素素 出现在哪些镜头 ===")
hits = 0
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if "素素" in (sh.characters or []):
                hits += 1
                if hits <= 8:
                    out.append(f"  ep{ep.index} {sh.id} 角色={sh.characters}")
                    out.append(f"      台词数={len(sh.line_indices or [])} "
                               f"action={str(sh.action)[:70]!r}")
out.append(f"  共 {hits} 镜")

out.append("")
out.append("=== 台词里说话的人 ===")
speakers: dict[str, int] = {}
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for ln in sc.lines:
            speakers[ln.speaker] = speakers.get(ln.speaker, 0) + 1
for k, v in sorted(speakers.items(), key=lambda x: -x[1]):
    mark = "" if any(c.name == k for c in (ctx.project.characters or [])) else "  **不在角色表**"
    out.append(f"  {k!r}: {v} 句{mark}")

out.append("")
out.append("=== 剧本/分镜里有没有素素的描述 ===")
src = proj / "source"
if src.exists():
    for f in src.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".txt", ".md"):
            t = f.read_text(encoding="utf-8", errors="replace")
            n = t.count("素素")
            if n:
                out.append(f"  {f.name}: 出现 {n} 次")
                i = t.find("素素")
                out.append(f"      …{t[max(0,i-60):i+80]}…".replace("\n", " "))

# how a character is normally born
out.append("")
out.append("=== character 阶段怎么创建角色 ===")
import inspect   # noqa: E402
from dramakit.pipeline import character as CH   # noqa: E402
src_ch = inspect.getsource(CH.run)
out.append(src_ch[:2200])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\susu.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
