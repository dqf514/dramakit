"""Did the stop mechanism land, and does the server import?

Checks each piece that has to be in place before the console can stop a
run: the event on the job record, the endpoint, the pipeline asking, and
the sweep that settles a stage a dead process left claiming to run.
"""
import ast
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

srv = Path(r"E:\dramakit\dramakit\web\server.py").read_text(encoding="utf-8")
ast.parse(srv)

checks = [
    ("server: 任务带 stop 事件", '"stop": stop' in srv),
    ("server: stop_job 方法", "def stop_job" in srv),
    ("server: running_jobs 方法", "def running_jobs" in srv),
    ("server: POST /api/jobs/stop", 'path == "/api/jobs/stop"' in srv),
    ("server: 处理函数", "def _api_jobs_stop" in srv),
]
for label, ok in checks:
    print(f"  [{'ok' if ok else 'MISSING'}]  {label}")

run = Path(r"E:\dramakit\dramakit\pipeline\runner.py").read_text(encoding="utf-8")
checks2 = [
    ("runner: 导入 RunStopped", "RunStopped" in run),
    ("runner: 阶段前检查", "if ctx.stopped:" in run),
    ("runner: 中断记为 INTERRUPTED", "Status.INTERRUPTED" in run),
]
for label, ok in checks2:
    print(f"  [{'ok' if ok else 'MISSING'}]  {label}")

base = Path(r"E:\dramakit\dramakit\pipeline\base.py").read_text(encoding="utf-8")
checks3 = [
    ("base: RunStopped 异常", "class RunStopped" in base),
    ("base: check_stop", "def check_stop" in base),
    ("base: bind_stop", "def bind_stop" in base),
]
for label, ok in checks3:
    print(f"  [{'ok' if ok else 'MISSING'}]  {label}")

mods = Path(r"E:\dramakit\dramakit\pipeline")
n = sum(1 for f in ("script", "storyboard", "promptgen", "voice", "visual", "compose")
        if "check_stop" in (mods / f"{f}.py").read_text(encoding="utf-8"))
print(f"  [{'ok' if n == 6 else 'PARTIAL'}]  逐集检查: {n}/6 个阶段")

print()
try:
    from dramakit.web import server  # noqa: F401
    print("server.py import OK")
except Exception as e:  # noqa: BLE001
    print(f"server.py import 失败: {type(e).__name__}: {e}")
