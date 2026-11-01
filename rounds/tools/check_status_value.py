"""Is the stage status really the string "Status.DONE", or was that the probe?

The probe printed str(v) for every status, and str() on an enum is its
repr - so a field holding Status.DONE prints as "Status.DONE" and looks
corrupt. This prints the value and the type, so a real defect is not
excused and a phantom is not chased.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore
from dramakit.models import Status

store = ProjectStore.open(Path(r"E:\dramakit\projects\妖怪志"))
ctx = Context(Config.load(Config.discover()), store)

e0 = ctx.project.episodes[0]
print("=== 第一集的 script 状态 ===")
v = (e0.stage_status or {}).get("script")
print(f"  repr : {v!r}")
print(f"  type : {type(v).__name__}")
print(f"  .value: {getattr(v, 'value', '(不是枚举)')}")
print(f"  == Status.DONE: {v == Status.DONE}")
print(f"  stage_done 判定: {ctx.stage_done(e0, 'script')}")

print()
print("=== 项目级状态 ===")
for k, val in ctx.project.stage_status.items():
    print(f"  {k:<10} {type(val).__name__:<10} {getattr(val, 'value', val)!r}")

print()
print("=== 序列化后（落盘的真值）===")
print(json.dumps(e0.model_dump().get("stage_status", {}), ensure_ascii=False))
