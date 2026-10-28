"""Try the shot split on a project without changing it."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.pipeline.storyboard import _split_long_shots
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
name = sys.argv[1]
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
proj = store.load()
ep = proj.episodes[0]
for sc in ep.scenes:
    added = _split_long_shots(sc)
    print(f"场景 {sc.index}: 拆出 {added} 个镜头，现在 {len(sc.shots)} 个")
    for sh in sc.shots:
        who = "、".join(sh.characters or []) or "（无人）"
        print(f"   {sh.index} {sh.shot_type.value:<4} {who:<14} "
              f"lines={sh.line_indices} 「{(sh.action or '')[:40]}」")

tl = build_timeline(ep, max_shot=cfg.comfyui.max_video_seconds,
                    line_gap=cfg.compose.line_gap)
print(f"\n总长 {tl.duration:.2f}s  {len(tl.shots)} 镜  "
      f"平均 {tl.duration/max(len(tl.shots),1):.2f}s")
