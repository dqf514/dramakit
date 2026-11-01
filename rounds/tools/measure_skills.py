"""What does each stage actually send, in characters?

Four stages load skills, and the prompt stage was measured at ten thousand
characters per video call. This puts a number on each of them, with and
without the references that nothing currently asks for, so the cost of a
skill list is visible rather than assumed.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.skills import loader

STAGES = {
    "analyze": ["short-drama-novel-analyze"],
    "script": ["short-drama-write"],
    "storyboard": ["short-drama-storyboard"],
    "promptgen": ["short-drama-video-prompts", "short-drama-image-prompts"],
}

out = []
for stage, names in STAGES.items():
    brief = sum(len(loader.load(n)) for n in names)
    full = sum(len(loader.load(n, refs=True)) for n in names)
    out.append(f"{stage:<12} {len(names)} 个 skill")
    for n in names:
        out.append(f"    {n:<34} {len(loader.load(n)):>8,} 字符")
    out.append(f"    {'小计（现用）':<34} {brief:>8,} 字符")
    out.append(f"    {'若含 references':<34} {full:>8,} 字符")
    out.append("")

# what the theory skills would cost, if a genre pulled them in
out.append("=== by_genre 会额外注入的（按 SKILL.md）===")
import dramakit.config as C
cfg = C.Config.load(C.Config.discover())
for key, extra in (cfg.skills.by_genre or {}).items():
    for n in extra:
        out.append(f"  频道含「{key}」时 +{n:<46} {len(loader.load(n)):>8,} 字符")

out.append("")
out.append("=== skills/ 里有多少可选 ===")
from pathlib import Path
root = Path(r"E:\dramakit\skills")
fams = {}
for p in sorted(root.iterdir()):
    if p.is_dir() and (p / "SKILL.md").exists():
        fam = p.name.split("-")[0] if "-" in p.name else p.name
        fams.setdefault(fam, []).append((p.name, (p / "SKILL.md").stat().st_size))
for fam, items in fams.items():
    out.append(f"  {fam:<22} {len(items):>3} 个 skill")
theory = [p for p in (root / "screenwriting-theory").iterdir()
          if p.is_dir() and (p / "SKILL.md").exists()]
out.append(f"  {'- 编剧理论明细':<22} {len(theory):>3} 个（共 "
           f"{sum((p / 'SKILL.md').stat().st_size for p in theory) / 1024:.0f} KB）")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\stagesizes.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
