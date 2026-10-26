"""Does the cast repair fix the line that was on the wrong shot?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.base import Context, build_timeline
from dramakit.pipeline.storyboard import _repair_line_casts
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / sys.argv[1]
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]

before = after = 0
for sc in ep.scenes:
    spoken = [l for l in sc.lines if not is_narration(l)]
    for sh in sc.shots:
        for n in sh.line_indices:
            if 1 <= n <= len(spoken):
                if spoken[n - 1].speaker not in (sh.characters or []):
                    before += 1
    moved = _repair_line_casts(sc)
    for sh in sc.shots:
        for n in sh.line_indices:
            if 1 <= n <= len(spoken):
                if spoken[n - 1].speaker not in (sh.characters or []):
                    after += 1
    if moved:
        print(f"场景 {sc.index}: 移动 {moved} 句")

print(f"修复前 {before} 句说话时镜头里是别人 -> 修复后 {after} 句")
