"""Run the QC checks against the finished episode files on disk."""
import sys
import json
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.project import ProjectStore
from dramakit.pipeline.base import Context
from dramakit.pipeline import qc

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\测试短剧")
store = ProjectStore(root)
ctx = Context(cfg, store)

for ep in ctx.target_episodes():
    f = root / "episodes" / f"ep_{ep.index:03d}.mp4"
    if not f.exists():
        print(f"ep{ep.index}: 无成片文件")
        continue
    ep.video_path = store.rel(f)
    rep = qc.check_episode(ctx, ep)
    print(f"=== ep{ep.index}  ok={rep['ok']} ===")
    print("  metrics:", json.dumps(rep["metrics"], ensure_ascii=False))
    for e in rep["errors"]:
        print("  ✗", e)
    for w in rep["warnings"]:
        print("  !", w)
