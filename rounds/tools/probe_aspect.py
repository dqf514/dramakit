"""Whether the picture matches the frame the script asked for, and what the
music stage is doing inside the drawing loop.

Two things came out of the log. The first is a picture that is landscape
while the shot's own prompt may well ask for vertical - a short drama is
shot for a phone, and a landscape frame of it is wrong however good the
image is. The second is a block of music lines repeating every few
seconds inside the drawing lane, which is either a stage running twice or
a loop that has nothing to do.

Both are read straight off the project: the prompts, the size the config
asks for, and where the music messages come from.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402

REPO = Path(r"E:\dramakit")
proj = REPO / "projects" / "星际骷髅兵"
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
cfg = Config.load(Config.discover())
out = []

out.append("=== 出图画幅 ===")
out.append(f"  配置 width x height = {cfg.comfyui.width} x {cfg.comfyui.height}")
ad = raw.get("art_direction") or {}
out.append(f"  项目画幅设定: {ad.get('aspect_ratio') or ad.get('ratio') or '(无)'} "
           f"canvas={ad.get('canvas') or '(无)'}")
for k in ("style", "style_prompt_prefix", "genre", "era", "color_palette"):
    if ad.get(k):
        out.append(f"  {k}: {str(ad[k])[:120]}")

out.append("")
out.append("=== 每个镜头的提示词里怎么说画幅 ===")
want = {}
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            p = sh.get("prompt") or ""
            if not p:
                continue
            m = re.search(r"(\d+\s*[x×:]\s*\d+|\d+\s*:\s*\d+|vertical|landscape|portrait|竖|横)",
                          p, re.I)
            key = (m.group(0).lower() if m else "(没提)")
            want[key] = want.get(key, 0) + 1
            if sum(want.values()) <= 6:
                out.append(f"    {sh.get('id')}: {p[:110]}")
for k, v in sorted(want.items(), key=lambda x: -x[1]):
    out.append(f"    {k}: {v} 镜")

# --- the music messages -------------------------------------------------
out.append("")
out.append("=== 「配乐镜头」这些消息来自哪里 ===")
for f in REPO.glob("dramakit/pipeline/*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "配乐镜头" in t or "所有镜头已生成" in t:
        for i, l in enumerate(t.split("\n"), 1):
            if "配乐镜头" in l or "所有镜头已生成" in l:
                out.append(f"  {f.name}:{i}: {l.strip()[:150]}")

# --- where the music stage is called from -------------------------------
out.append("")
out.append("=== 谁调用了 music 阶段 ===")
for f in REPO.glob("dramakit/pipeline/*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    for i, l in enumerate(t.split("\n"), 1):
        if re.search(r"\bmusic(_stage)?\b.*(run|import)|from \.music|import music", l):
            out.append(f"  {f.name}:{i}: {l.strip()[:150]}")

out.append("")
out.append("=== runner 里 WRITES/TAIL 的分组 ===")
t = (REPO / "dramakit/pipeline/runner.py").read_text(encoding="utf-8")
for i, l in enumerate(t.split("\n"), 1):
    if re.match(r"^(SETUP|WRITES|DRAWS|TAIL|ORDER)\s*=", l):
        out.append(f"  {i}: {l}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\aspect.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
