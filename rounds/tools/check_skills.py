"""Do the four stages write with a skill?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore
from dramakit.skills import loader

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母")))
print("题材:", ctx.project.art_direction.genre)
for stage in ("analyze", "script", "storyboard", "promptgen"):
    t = loader.for_stage(ctx, stage)
    print(f"  {stage:<11} {len(t):>6} 字   {t[:60].splitlines()[1] if chr(10) in t[:60] else t[:60]}")
