"""Who 素素 is, from the book itself.

She speaks thirty lines and shares six shots, and the cast never got an
entry for her. Before an entry can be written her appearance has to come
from somewhere, and the only source that knows is the text the script was
cut from - so the passages that name her are pulled out, along with what
the other characters are described as, since a new face has to sit beside
them rather than contradict them.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())

# --- every passage naming her -----------------------------------------
out.append("=== 原著里提到素素的段落 ===")
src = proj / "source"
seen = set()
for f in sorted(src.rglob("*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer("素素", t):
        i = m.start()
        # a window on either side, on paragraph boundaries
        lo = t.rfind("\n", 0, i)
        hi = t.find("\n", i)
        para = t[(lo + 1) if lo >= 0 else 0: hi if hi > 0 else len(t)].strip()
        key = para[:60]
        if key in seen or len(para) < 10:
            continue
        seen.add(key)
        out.append(f"  [{f.name}]")
        out.append(f"    {para[:400]}")
        out.append("")

# --- how she is credited in the script --------------------------------
out.append("=== 分镜里素素的戏份 ===")
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            if "素素" in (sh.get("characters") or []):
                out.append(f"  ep{ep.get('index')} {sh.get('id')}")
                out.append(f"    action: {str(sh.get('action'))[:260]}")
                out.append(f"    prompt: {str(sh.get('prompt'))[:200]}")
                out.append("")

# --- the other characters' descriptions, for tone and continuity -------
out.append("=== 已有角色的外貌描述（新角色要与之一致）===")
for c in raw.get("characters") or []:
    if not isinstance(c, dict):
        continue
    if c.get("name") in ("余飞", "余母", "郭浩"):
        out.append(f"  {c.get('name')}:")
        for k in ("role", "gender", "age", "appearance", "visual_prompt",
                  "hair", "outfit"):
            v = c.get(k)
            if v:
                out.append(f"    {k}: {str(v)[:300]}")
        out.append("")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\susu_src.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
