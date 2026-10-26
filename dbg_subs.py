"""Look for subtitle cues that sit on top of each other."""
import re
import sys
from pathlib import Path


def ass_time(s: str) -> float:
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


for name in ("轮次01_01", "轮次02_02", "轮次03_03"):
    p = Path(r"E:\dramakit\projects") / name / "subtitles" / "ep_001.ass"
    if not p.exists():
        cand = list((Path(r"E:\dramakit\projects") / name).rglob("*.ass"))
        if not cand:
            print(name, "没有 ASS")
            continue
        p = cand[0]
    cues = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        f = line.split(",", 9)
        body = re.sub(r"\{[^}]*\}", "", f[-1]).replace("\\N", " ").strip()
        cues.append((ass_time(f[1]), ass_time(f[2]), f[3], body))
    # only the dialogue line of each cue, not the speaker label
    main = [c for c in cues if c[2] in ("Default", "Narration")]
    bad = []
    for i in range(len(main) - 1):
        a, b = main[i], main[i + 1]
        if a[2] != b[2]:
            continue
        if a[1] > b[0] + 0.001:
            bad.append((a, b, a[1] - b[0]))
    print(f"{name}: {len(main)} 条字幕，重叠 {len(bad)} 处")
    for a, b, d in bad[:5]:
        print(f"   重叠 {d:.2f}s  [{a[3][:18]}] {a[0]:.2f}-{a[1]:.2f}  ->  "
              f"[{b[3][:18]}] {b[0]:.2f}")
