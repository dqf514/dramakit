"""The storyboard's assignment against the timeline's."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _dialogue_by_shot
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\\tmp\\ep23")
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 2
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episode(ep_index)
dlg = _dialogue_by_shot(ctx, ep)
tl = ctx.timeline(ep)

for tsc in tl.scenes:
    spoken = [l for l in tsc.scene.lines if l.kind.value != "narration"]
    print("=" * 60)
    for ts in tsc.shots:
        sh = ts.shot
        owned = [spoken[n - 1].text[:10] for n in (sh.line_indices or [])
                 if 1 <= n <= len(spoken)]
        got = [t[1][:10] for t in dlg.get(sh.id, [])]
        mark = "  " if owned == got else "≠ "
        print(f"{mark}{sh.id[:14]} [{ts.start:6.2f},{ts.start+ts.duration:6.2f}] "
              f"分镜表={owned} 时间线={got}")
