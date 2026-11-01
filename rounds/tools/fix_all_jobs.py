"""Every _job now takes an argument, so every _job has to accept it.

start_job hands the thread an event so a run can be stopped. That changed
what the thread passes, and the health endpoint keeps a _job of its own
that nobody thought about - so the console came up reporting a failed
health probe on every request. The change was right; the sweep over the
callers was not complete.

This finds every _job the server defines and gives each one the argument,
so the next one added is not a surprise either.
"""
import re
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

# 1. the import the sweep needs
if "from ..models import Status" not in s:
    old = "from ..project import ProjectStore"
    assert old in s
    s = s.replace(old, "from ..models import Status\n" + old, 1)
    print("server.py: 导入 Status")

# 2. every zero-arg _job becomes one that takes the event
pattern = re.compile(r"def _job\(\):")
found = pattern.findall(s)
s = pattern.sub("def _job(stop=None):", s)
print(f"server.py: {len(found)} 个 _job 改为接受 stop")

# and the ones called with an explicit report keep working:
#   def _job(report_progress, stop) -> already correct
#   fn(stop) inside _wrap passes the event positionally, which the
#   default absorbs when a job does not care about it
p.write_text(s, encoding="utf-8")
print("server.py: 全部 _job 现在都能接住 stop")
