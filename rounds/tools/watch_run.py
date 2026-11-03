"""Keep an eye on the run while it goes, from a process of its own.

A run of this length is unattended, and the interesting part is not the
progress - it is the moments where something goes wrong. So this follows
the job, writes every line the console logs, and picks out the ones that
matter: a stage that failed, a stage that was stopped, an error, a
warning that is not just a retry, and the moment a stage begins and
ends.

It also times the stages, because the timings are what tell you where
the pipeline actually spends its time - and where a slow stage is a bug
rather than the work being slow.

Started detached (Start-Process), so it keeps going when the console
it was started from goes away.
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

CONSOLE = "http://127.0.0.1:8080"
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\run_watch.txt")
seen: set = set()
stage_start: dict[str, float] = {}
stages: dict[str, float] = {}
t0 = time.time()
DEADLINE = t0 + 48 * 3600


def get(path, timeout=30):
    try:
        with urllib.request.urlopen(CONSOLE + path, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:  # noqa: BLE001
        return {}


def note(lines):
    with OUT.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


STAGE_RE = re.compile(r"── 阶段 \[(\w+)\] (开始|完成|已停止|失败)")
note([f"=== 监控开始 {time.strftime('%H:%M:%S')} ==="])

while time.time() < DEADLINE:
    try:
        with urllib.request.urlopen(CONSOLE + "/api/logs?lines=400", timeout=30) as r:
            lines = json.loads(r.read()).get("lines") or []
    except Exception:  # noqa: BLE001
        time.sleep(15)
        continue

    for l in lines:
        # the log is re-read every pass, so lines are matched by when they
        # were written and what they say - an id would be new each time
        key = (l.get("t"), (l.get("msg") or "")[:80])
        if key in seen:
            continue
        seen.add(key)
        m = l.get("msg") or ""
        mm = STAGE_RE.search(m)
        if mm:
            stage, what = mm.group(1), mm.group(2)
            ts = time.time()
            if what == "开始":
                stage_start[stage] = ts
                note([f"[{time.strftime('%H:%M:%S')}] ▶ {stage} 开始"])
            else:
                dur = ts - stage_start.pop(stage, ts)
                stages[stage] = dur
                note([f"[{time.strftime('%H:%M:%S')}] {what} {stage} "
                      f"({dur/60:.1f} 分)"])
        elif l.get("lv") in ("e", "w"):
            # a client that hangs up is not the pipeline's fault
            if "ConnectionAbortedError" in m or "BrokenPipeError" in m:
                continue
            note([f"[{time.strftime('%H:%M:%S')}] [{l.get('lv')}] {m[:300]}"])

    # the job's own state
    jobs = get("/api/jobs").get("jobs") or []
    run = next((j for j in jobs if j.get("kind") == "run_pipeline"), None)
    if run and run.get("status") not in ("running", "queued"):
        note([f"[{time.strftime('%H:%M:%S')}] 任务结束 status={run.get('status')} "
              f"error={str(run.get('error'))[:300]}"])
        note(["阶段耗时:"] + [f"  {k}: {v/60:.1f} 分" for k, v in stages.items()])
        break
    time.sleep(10)

note([f"=== 监控结束 {time.strftime('%H:%M:%S')} ==="])
