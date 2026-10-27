"""Check the music-only prompt for a scene."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _gen_score_prompt
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
name = sys.argv[1]
store = ProjectStore(Path(r"E:\dramakit\projects") / name)
ctx = Context(cfg, store)
llm = ctx.providers.llm_for("promptgen")
ep = ctx.target_episodes()[0]
for sc in ep.scenes:
    _gen_score_prompt(ctx, llm, sc)
    print(f"=== 场景 {sc.index} {sc.location} {sc.time_of_day} 情绪 {sc.mood}")
    print(sc.score_prompt[:700])
    print()
