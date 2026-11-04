"""Compose the finished episode while the cards keep working.

The pipeline's own order puts the film at the end, after every shot of
every episode has been drawn. The first episode is finished; the other
two are not, and that is hours away.

So the tail is run here, in a process of its own, for the first episode
only. Two things make that safe:

- its own config, so the episodes it is told to do are not the ones
  the running pipeline is doing;
- the merge that happens before every write, so the two of them can
  write the same file without losing each other's work: the film that
  is finished is taken in, and so is every clip that is on the disk.

The cards are not touched. The rendering goes on while this runs.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.project import ProjectStore
from dramakit.pipeline.base import Context
from dramakit.pipeline import (compose as compose_stage, lipsync as lipsync_stage,
                               precheck as precheck_stage, qc as qc_stage,
                               subtitle as subtitle_stage)

PROJ = Path(r"E:\dramakit\projects\星际骷髅兵")
EPISODE = 1

cfg = Config.load(Config.discover())
# only the episode that is finished - this config is this process's own
cfg.pipeline.only_episodes = [EPISODE]
store = ProjectStore.open(PROJ)
ctx = Context(cfg, store)

eps = ctx.target_episodes()
print("=== 要做的集 ===")
for ep in eps:
    shots = [sh for sc in ep.scenes for sh in sc.shots]
    done = sum(1 for sh in shots if getattr(sh, "video_path", ""))
    print(f"  第{ep.index}集 {ep.title}  镜 {len(shots)}  有片 {done}  时长 {ctx.timeline(ep).duration:.0f} 秒")

for name, mod in (("lipsync", lipsync_stage), ("subtitle", subtitle_stage),
                   ("precheck", precheck_stage), ("compose", compose_stage),
                   ("qc", qc_stage)):
    print()
    print(f"=== {name} ===", flush=True)
    t0 = time.time()
    try:
        res = mod.run(ctx)
        print(f"  {time.time()-t0:.0f} 秒 -> {json.dumps(res, ensure_ascii=False)[:300]}")
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"  失败（{time.time()-t0:.0f} 秒）: {type(e).__name__}: {str(e)[:300]}")
        traceback.print_exc()

print()
print("=== 结果 ===")
proj = store.load()
for ep in proj.episodes:
    print(f"  第{ep.index}集 成片={ep.video_path}  字幕={ep.subtitle_path}  "
          f"阶段={ {k: str(v) for k, v in (ep.stage_status or {}).items()} }")
