"""What do the H3 prompts actually ask for? Look for vocal descriptions."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

WORDS = ["speaks", "says", "voice", "talking", "speaking", "shouts", "whispers",
         "murmur", "dialogue", "conversation", "argues", "replies", "utters"]
for name in sys.argv[1:]:
    proj = Path(r"E:\dramakit\projects") / name
    store = ProjectStore(proj)
    p = store.load()
    hits = 0
    total = 0
    for ep in p.episodes:
        for sc in ep.scenes:
            for sh in sc.shots:
                vp = sh.video_prompt or ""
                if not vp:
                    continue
                total += 1
                found = [w for w in WORDS if w in vp.lower()]
                if found:
                    hits += 1
                    if hits <= 3:
                        print(f"  {sh.id} 含 {found}")
                        for m in re.findall(r"[^.]*\b(?:" + "|".join(found) + r")\b[^.]*\.",
                                           vp, re.I):
                            print(f"      …{m.strip()[:150]}")
    print(f"{name}: {hits}/{total} 个 H3 提示词里提到了发声")
    # also: does the prompt carry the actual dialogue?
    dlg = 0
    for ep in p.episodes:
        for sc in ep.scenes:
            for sh in sc.shots:
                if "<d>" in (sh.video_prompt or ""):
                    dlg += 1
    print(f"   带 <d> 台词标签的提示词: {dl}")
