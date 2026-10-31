"""Why did a line not reach the prompt?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _dialogue_by_shot
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1
            else r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [1]
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))

for ep in ctx.project.episodes:
    if ep.index not in eps:
        continue
    tl = ctx.timeline(ep)
    dlg = _dialogue_by_shot(ctx, ep)
    for tsc in tl.scenes:
        for tl_line in tsc.lines:
            if tl_line.line.kind.value == "narration":
                continue
            placed = [ts.shot.id for ts in tsc.shots
                      if ts.start <= tl_line.start < ts.start + ts.duration]
            owner = placed[0] if placed else None
            in_map = owner in dlg and any(
                t[1] == tl_line.line.text for t in dlg.get(owner, []))
            if not in_map:
                print(f"没进提示词: 「{tl_line.line.text}」 {tl_line.line.speaker} "
                      f"@{tl_line.start:.2f}-{tl_line.end:.2f}  镜头窗口: "
                      + ", ".join(f"{ts.shot.id[:12]}[{ts.start:.2f},"
                                  f"{ts.start+ts.duration:.2f})" for ts in tsc.shots))
                print(f"    分镜表的归属: "
                      + ", ".join(f"{sh.id[:12]}->{sh.line_indices}"
                                  for sh in tsc.scene.shots))
