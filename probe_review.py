"""What does the model actually answer to the review prompt?"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.review import SYSTEM, _facts, _frames
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\轮次09_09")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.target_episodes()[0]
tmp = root / "tmp" / "review"
tmp.mkdir(parents=True, exist_ok=True)
frames = _frames(ctx, ep, tmp, limit=6)
print(f"帧数 {len(frames)}")
llm = ctx.providers.llm_for("review")
r = llm.complete_vision(SYSTEM, _facts(ctx, ep), [str(p) for p in frames],
                        temperature=0.2, max_tokens=4000)
print(f"文本长度 {len(r.text)}")
print(r.text[:1500])
