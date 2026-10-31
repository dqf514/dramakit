"""The scene's lines, with the index the storyboard used."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.models import is_narration
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\\tmp\\ep23")
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 2
shot_id = sys.argv[3] if len(sys.argv) > 3 else "sh-436d8d84"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episode(ep_index)

for sc in ep.scenes:
    if not any(sh.id == shot_id for sh in sc.shots):
        continue
    print("场景", sc.index, sc.location)
    spoken = [l for l in sc.lines if not is_narration(l)]
    for i, l in enumerate(spoken, 1):
        print(f"   第{i}句 {l.speaker} 「{l.text[:20]}」")
    print("  分镜表的分配:")
    for sh in sc.shots:
        owned = [spoken[n - 1].text[:14] for n in (sh.line_indices or [])
                 if 1 <= n <= len(spoken)]
        print(f"    {sh.id[:14]} {sh.line_indices} -> {owned}")
