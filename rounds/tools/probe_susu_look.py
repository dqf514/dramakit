"""What the existing prompts already say she looks like.

The shots that feature her were written before she had a character entry,
so any description of her in them was invented on the spot by the model
that wrote them. Those prompts are what the video will be rendered from,
and a reference sheet drawn from a different idea of her face would fight
them in every frame - so her appearance is read back out of them rather
than made up again here.
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
out.append("=== 素素所在镜头的完整提示词 ===")
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            if "素素" not in (sh.get("characters") or []):
                continue
            p = sh.get("video_prompt") or sh.get("prompt") or ""
            if not p:
                continue
            out.append(f"--- {sh.get('id')} ({len(p)} 字符) ---")
            # the sentences that mention her
            for sent in re.split(r"(?<=[.。;；])\s*", p):
                if "素素" in sent or "Susu" in sent or "Su Su" in sent:
                    out.append(f"  含她: {sent.strip()[:400]}")
            out.append("")

# --- every distinct description of a young woman in the prompts ---------
out.append("=== 提示词里出现的女性外貌描述（找她的原型）===")
seen = set()
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            p = sh.get("video_prompt") or sh.get("prompt") or ""
            for m in re.finditer(
                    r"[^.;]*\b(young woman|girl|female|she|her)\b[^.;]*[.;]",
                    p, re.I):
                s = m.group(0).strip()
                if len(s) < 40 or s in seen:
                    continue
                seen.add(s)
                out.append(f"  [{sh.get('id')}] {s[:320]}")
            if len(seen) > 25:
                break
        if len(seen) > 25:
            break
    if len(seen) > 25:
        break

# --- the storyboard's own cast note, if any ----------------------------
out.append("")
out.append("=== 分镜/剧本里对她的说明 ===")
for ep in raw.get("episodes") or []:
    if ep.get("index") != 6:
        continue
    for k in ("synopsis", "summary", "cast", "notes"):
        v = ep.get(k)
        if v:
            out.append(f"  {k}: {str(v)[:600]}")

# --- the source, wider window ------------------------------------------
out.append("")
out.append("=== 原著里更宽的上下文（找外貌）===")
src = proj / "source"
for f in sorted(src.rglob("*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer("素素", t):
        i = m.start()
        lo = max(0, i - 300)
        hi = min(len(t), i + 300)
        win = t[lo:hi]
        if any(k in win for k in ("头发", "眼睛", "笑容", "长发", "裙子",
                                  "漂亮", "好看", "脸", "身高", "岁")):
            out.append(f"  [{f.name}] …{win}…")
            out.append("")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\susu_look.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
