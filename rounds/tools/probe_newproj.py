"""What the new project looks like before anything is run on it.

A chapter of a long book is not the whole book: the cast, the rooms and
the volume of the story all arrive in one go, and the run has to be told
to keep to the first chapter. So what is here is read before it is
started - how many characters the analysis found, which of them have
pictures, how many rooms, and where the last run stopped.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402

REPO = Path(r"E:\dramakit")
out = []
cfg = Config.load(Config.discover())
proj = REPO / "projects" / "星际骷髅兵"
store = ProjectStore.open(proj)
ctx = Context(cfg, store, Providers(cfg, REPO))

raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
m = raw.get("meta") or {}

out.append("=== meta ===")
for k in ("name", "title", "source_file", "genre", "style", "synopsis"):
    v = m.get(k)
    if v:
        out.append(f"  {k}: {str(v)[:200]}")
out.append(f"  chapters: {len(m.get('chapters') or [])}")
out.append(f"  chosen_chapters: {m.get('chosen_chapters')}")
out.append(f"  segmented_chapters: {m.get('segmented_chapters')}")
out.append(f"  chapter_season: {str(m.get('chapter_season'))[:200]}")
out.append(f"  episodes_wanted: {m.get('episodes_wanted')}")
out.append(f"  skills: {m.get('skills')}")
out.append(f"  last_run: {str(m.get('last_run'))[:200]}")

out.append("")
out.append("=== 阶段 ===")
for k, v in (raw.get("stage_status") or {}).items():
    out.append(f"  {k:14} {v}")

chars = raw.get("characters") or []
out.append("")
out.append(f"=== 角色 {len(chars)} 个 ===")
have_refs = 0
have_voice = 0
for c in chars[:12]:
    if not isinstance(c, dict):
        continue
    refs = [r for r in (c.get("ref_images") or []) if (proj / r).exists()]
    v = c.get("voice_ref")
    have_refs += 1 if refs else 0
    have_voice += 1 if v and (proj / v).exists() else 0
    out.append(f"  {str(c.get('name')):16} role={str(c.get('role')):8} "
               f"refs={len(refs)} voice={'有' if v and (proj/v).exists() else '无'} "
               f"anchor={'有' if c.get('anchor_prompt') else '无'}")
out.append(f"  ... 共 {len(chars)} 个；有参考图的 {have_refs}，有配音的 {have_voice}")

locs = raw.get("locations") or []
out.append("")
out.append(f"=== 场景 {len(locs)} 个 ===")
for l in locs[:6]:
    if isinstance(l, dict):
        refs = [r for r in (l.get("ref_images") or []) if (proj / r).exists()]
        out.append(f"  {str(l.get('name')):20} refs={len(refs)}")

props = raw.get("props") or []
out.append(f"  道具 {len(props)} 个")

out.append("")
out.append("=== 集 ===")
eps = raw.get("episodes") or []
out.append(f"  {len(eps)} 集")
for ep in eps[:8]:
    if not isinstance(ep, dict):
        continue
    shots = sum(len(sc.get("shots") or []) for sc in ep.get("scenes") or [])
    out.append(f"  ep{ep.get('index')} {str(ep.get('title'))[:24]:26} "
               f"场={len(ep.get('scenes') or [])} 镜={shots} "
               f"stage={ {k: v for k, v in (ep.get('stage_status') or {}).items()} }")

out.append("")
out.append("=== 第一章原文（前 600 字）===")
vol_dir = proj / "source" / "volumes"
if vol_dir.exists():
    for f in sorted(vol_dir.glob("*_ch001.txt")):
        t = f.read_text(encoding="utf-8", errors="replace")
        out.append(f"  {f.name}  {len(t)} 字")
        out.append("  " + t[:600].replace("\n", "\n  "))

# what's on disk
out.append("")
out.append("=== 磁盘 ===")
for sub in ("characters", "images", "video", "audio", "episodes", "subs", "locations"):
    d = proj / sub
    n = len([f for f in d.rglob("*") if f.is_file()]) if d.exists() else 0
    out.append(f"  {sub:12} {n:>5}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\newproj.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
