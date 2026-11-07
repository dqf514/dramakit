"""What did the planner actually say?

The episode came out with no scenes at all, so the planner's answer is
looked at as it came - not as it was parsed.
"""
import json
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline import make_context  # noqa: E402
from dramakit.pipeline.base import llm_pool  # noqa: E402
from dramakit.prompts import templates as T  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402
from dramakit.skills import loader  # noqa: E402
from dramakit.skills.film import DIRECTOR_RULES, SCREENWRITER_RULES  # noqa: E402

cfg = Config.load(Config.discover())
store = ProjectStore.open(r"E:\dramakit\projects\我死后-仙尊追悔莫及")
ctx = make_context(cfg, store)
ep = ctx.target_episodes()[0]
block = ctx.store.abs(ep.source_path).read_text(encoding="utf-8")

rules = (SCREENWRITER_RULES + loader.for_stage(ctx, "script")
         + loader.genre_rules(ctx, "script") + DIRECTOR_RULES)
print("  规矩 %d 字" % len(rules))

pool = llm_pool(ctx, "script")
user = T.render(T.SCRIPT_PLAN_USER,
                genre=ctx.project.art_direction.genre,
                min_scenes=2, max_scenes=8,
                screenwriter_rules=rules,
                character_names=", ".join(c.name for c in ctx.project.characters),
                location_names=", ".join(l.name for l in ctx.project.locations),
                text=block[:12000])
print("  提示词 %d 字" % len(user))
raw = pool.next().complete_json(T.SCRIPT_PLAN_SYSTEM, user)
print("\n=== 返回的类型：%s" % type(raw).__name__)
if isinstance(raw, list):
    raw = raw[0] if raw else {}
print("=== 键：%s" % list(raw.keys()))
print(json.dumps(raw, ensure_ascii=False, indent=2)[:4000])
