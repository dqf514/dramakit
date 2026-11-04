"""Why did the script stage write nothing?

It reported "episodes_scripted: 0" and finished in the same second, so
it never reached the model.  This walks the same path the stage walks
and says where it stops.
"""
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
store = ProjectStore.open(r"E:\dramakit\projects\魔兽永恒之树")
ctx = Context(cfg, store)

print("工程:", store.load().meta.title)
print("cfg.pipeline.only_episodes:", cfg.pipeline.only_episodes)
print("cfg.pipeline.stages_enabled:", cfg.pipeline.stages_enabled)
print("season_scoped:", ctx.season_scoped, "season_index:", ctx.season_index)

eps = ctx.target_episodes()
print(f"\ntarget_episodes() 返回 {len(eps)} 集:",
      [(e.index, e.title[:14]) for e in eps])
for ep in eps:
    print(f"\n第{ep.index}集《{ep.title}》")
    print("   source_path:", repr(ep.source_path))
    print("   stage_status:", {k: (v.value if hasattr(v, 'value') else v)
                               for k, v in (ep.stage_status or {}).items()})
    print("   stage_done('script'):", ctx.stage_done(ep, "script"),
          "| 有场:", bool(ep.scenes))
    try:
        block = ctx.store.abs(ep.source_path).read_text(encoding="utf-8") \
            if ep.source_path else ""
        print("   原文长度:", len(block), "| 前 80 字:", block[:80].replace("\n", " "))
    except Exception as e:  # noqa: BLE001
        print("   读原文失败:", type(e).__name__, e)
