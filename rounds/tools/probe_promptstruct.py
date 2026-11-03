"""Where the picture numbers live in a prompt, and whether only they changed.

Every prompt names its pictures by position, and the positions moved when
the face and the sheet became one picture. Rewriting a whole prompt to fix
a header risks losing the scene the writer chose; rewriting only the header
keeps it - if the numbers really are all in one place.

So a prompt is printed in full and the lines carrying a picture reference
are marked, to see whether they form a block that can be swapped or are
scattered through the description.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

out = []
# find a shot with the most picture references
best = None
best_n = 0
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            p = sh.get("prompt") or ""
            n = len(re.findall(r"<Picture \d+>", p))
            if n > best_n:
                best_n, best = n, (sh, p)

if not best:
    out.append("没有找到带提示词的镜头")
else:
    sh, p = best
    out.append(f"=== {sh.get('id')}（{len(p)} 字符，{best_n} 处图片引用）===")
    out.append("")
    lines = p.split("\n")
    for i, line in enumerate(lines, 1):
        mark = "  <<<" if re.search(r"<Picture \d+>", line) else ""
        out.append(f"{i:3}| {line[:200]}{mark}")
    if len(lines) > 60:
        out.append(f"... 共 {len(lines)} 行")

# --- how the picture lines are distributed ------------------------------
out.append("")
out.append("=== 所有提示词中 <Picture N> 出现的位置分布 ===")
pos_count: dict[int, int] = {}
total_prompts = 0
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            p = sh.get("prompt") or ""
            if not p:
                continue
            total_prompts += 1
            for i, line in enumerate(p.split("\n")):
                if re.search(r"<Picture \d+>", line):
                    pos_count[i] = pos_count.get(i, 0) + 1
out.append(f"  有提示词的镜头: {total_prompts}")
for k in sorted(pos_count)[:25]:
    out.append(f"    第 {k} 行: {pos_count[k]} 次")

# --- also the video prompt ---------------------------------------------
out.append("")
n_video = 0
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            if sh.get("video_prompt"):
                n_video += 1
out.append(f"  有 video_prompt 的镜头: {n_video}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\promptstruct.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
