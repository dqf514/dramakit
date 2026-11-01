"""Does check_stop raise, and does the event reach it?

The endpoint accepted the stop and the loop has the check, yet a run kept
going for a minute. Before believing the wiring, the pieces are tested
alone: the event raises, the context sees it, and a bound event is the
same object the endpoint sets.
"""
import sys
import threading

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline.base import Context, RunStopped
from dramakit.project import ProjectStore
from pathlib import Path

store = ProjectStore.open(Path(r"E:\dramakit\projects\妖怪志"))
ctx = Context(Config.load(Config.discover()), store)

print("=== 没绑事件 ===")
print("  stopped:", ctx.stopped)
try:
    ctx.check_stop()
    print("  check_stop: 没有抛（正确）")
except RunStopped:
    print("  check_stop: 抛了（不该）")

print()
print("=== 绑了事件但没设 ===")
ev = threading.Event()
ctx.bind_stop(ev)
print("  stopped:", ctx.stopped)

print()
print("=== 设了事件 ===")
ev.set()
print("  stopped:", ctx.stopped)
try:
    ctx.check_stop()
    print("  check_stop: 没有抛（错误！）")
except RunStopped:
    print("  check_stop: 抛了 RunStopped（正确）")

print()
print("=== RunStopped 是不是 Exception 的子类 ===")
print("  issubclass(Exception):", issubclass(RunStopped, Exception))

print()
print("=== runner 的 except 顺序 ===")
import inspect
from dramakit.pipeline import runner
src = inspect.getsource(runner.run_pipeline)
i = src.find("except")
print(src[i:i + 260])
