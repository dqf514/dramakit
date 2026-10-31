"""Where does a line that the storyboard gave to one shot actually live?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\\tmp\\ep23")
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 2
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episode(ep_index)

for sc in ep.scenes:
    spoken = [l for l in sc.lines if l.kind.value != "narration"]
    for sh in sc.shots:
        owned = [spoken[n - 1] for n in (sh.line_indices or [])
                 if 1 <= n <= len(spoken)]
        for l in owned:
            if l.text in (sh.video_prompt or ""):
                continue
            # where is it?
            where = [s2.id for s2 in sc.shots
                     if l.text in (s2.video_prompt or "")]
            print(f"「{l.text}」({l.speaker}) 分镜表给 {sh.id}，"
                  f"提示词里在: {where or '哪都没有'}")
