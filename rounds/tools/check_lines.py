"""Which lines are not in the prompt, and does the loose check see them?"""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _bare, _said
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
    for tsc in tl.scenes:
        for ts in tsc.shots:
            shot = ts.shot
            vp = shot.video_prompt or ""
            if not vp:
                continue
            spoken = [l for l in tsc.scene.lines if l.kind.value != "narration"]
            owned = [spoken[n - 1] for n in (shot.line_indices or [])
                     if 1 <= n <= len(spoken)]
            for l in owned:
                if l.text in vp:
                    continue
                loose = _said(vp, l.text)
                print(f"{shot.id} 「{l.text}」 精确=False 宽松={loose} "
                      f"<d>数={vp.count('<d>')}")
                if loose:
                    bare = _bare(l.text)
                    body = _bare(vp)
                    i = body.find(bare)
                    print("    宽松匹配到的地方:", vp[max(0, i - 40):i + 60].replace("\n", " "))
