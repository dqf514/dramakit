import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\测试短剧")
store = ProjectStore(root)
ctx = Context(cfg, store)
ep = ctx.project.episodes[0]
tl = build_timeline(ep)
print("tl.lines:", len(tl.lines))
for t in tl.lines:
    ap = t.line.audio_path
    exists = store.abs(ap).exists() if ap else False
    print(f"  narration={t.is_narration!s:5s} audio_path={ap!r:34s} exists={exists} "
          f"speaker={t.line.speaker!r}")
