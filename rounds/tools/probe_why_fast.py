"""Why did the script stage finish in five seconds over 151 episodes?

It did not run them: either the loop saw none, or every one was already
skipped. The difference matters, because a stage that silently does
nothing and reports success is the kind of bug that wastes a day before
anyone notices.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

store = ProjectStore.open(Path(r"E:\dramakit\projects\妖怪志"))
cfg = Config.load(Config.discover())
ctx = Context(cfg, store)

out = []
out.append("=== 项目 ===")
out.append(f"  episodes: {len(ctx.project.episodes)}")
out.append(f"  current_season: {ctx.project.current_season}")
out.append(f"  seasons 记录: {[s.index for s in (ctx.project.seasons or [])]}")
out.append(f"  season_index (Context): {ctx.season_index}")
out.append(f"  only_episodes: {cfg.pipeline.only_episodes}")

eps = ctx.target_episodes()
out.append("")
out.append("=== target_episodes() ===")
out.append(f"  返回: {len(eps)} 集")
if ctx.project.episodes:
    e0 = ctx.project.episodes[0]
    out.append(f"  第一集 season 字段: {getattr(e0, 'season', '（无此字段）')}")
    out.append(f"  第一集 stage_status: {json.dumps({k: str(v) for k, v in (e0.stage_status or {}).items()}, ensure_ascii=False)}")
    out.append(f"  第一集 scenes: {len(e0.scenes)}")
    out.append(f"  第一集 status: {e0.status}")

# how many would be skipped by the script guard
if eps:
    done = [e for e in eps if ctx.stage_done(e, "script") and e.scenes]
    out.append("")
    out.append(f"  其中已写完剧本且有场景（会被跳过）: {len(done)}")

out.append("")
out.append("=== 每集的 season 分布 ===")
from collections import Counter
c = Counter(getattr(e, "season", None) for e in ctx.project.episodes)
out.append("  " + json.dumps({str(k): v for k, v in c.items()}))

Path(r"C:\Users\David\AppData\Local\Temp\opencode\whyfast.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
