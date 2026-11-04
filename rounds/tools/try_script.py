"""What does the screenwriter make of a chapter of the novel?

The complaint was that the adaptation came out as a thin summary with
no logic to it.  This asks the model for one episode from a real chapter
and prints the scene list, so the result can be read rather than trusted.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.prompts import templates as T
from dramakit.providers.llm import OpenAICompatLLM
from dramakit.skills import loader

cfg = Config.load(r"E:\dramakit\config\default.yaml")
llm = OpenAICompatLLM(cfg.resolve_llm("script"))

import pathlib

base = pathlib.Path(r"E:\dramakit\projects\_trash")
cands = sorted(base.glob("*/source/volumes/*.txt"))
text = ""
for c in cands:
    t = c.read_text(encoding="utf-8", errors="replace")
    if len(t) > 3000:
        path = c
        text = t[:12000]
        break
print("原文：", path.name, len(text), "字\n")


class _P:
    class meta:
        skills = {}

    class art_direction:
        genre = "科幻/末日"


class _C:
    cfg = cfg
    project = _P()


rules = T.SCREENWRITER_RULES if hasattr(T, "SCREENWRITER_RULES") else ""
from dramakit.skills.film import SCREENWRITER_RULES
rules = SCREENWRITER_RULES + loader.for_stage(_C(), "script")
print("注入的编剧规矩：", len(rules), "字符\n")

user = T.render(
    T.SCRIPT_USER, genre="科幻末日", min_scenes=2, max_scenes=8,
    screenwriter_rules=rules,
    character_names="林远, 苏念, 老陈",
    location_names="废城街道, 避难所, 修理铺",
    text=text, budget_seconds=300, budget_chars=1350, budget_lines=66)

data = llm.complete_json(T.SCRIPT_SYSTEM, user)
if isinstance(data, list):
    data = data[0] if data else {}
scenes = data.get("scenes") or []
print(f"模型给了 {len(scenes)} 场：\n")
total = 0
for sc in scenes:
    lines = sc.get("lines") or []
    print(f"【{sc.get('location','')} · {sc.get('time_of_day','')}】"
          f"{sc.get('summary','')}   情绪={sc.get('mood','')}")
    for l in lines:
        total += len(l.get("text") or "")
        who = l.get("speaker", "")
        print(f"    {who}（{l.get('emotion','')}）: {l.get('text','')}")
    print()
print("台词总字数:", total)
