"""A run can be asked to stop, and a restart settles what it left behind.

The job lived in a daemon thread with no flag anyone could raise, so a
plan that turned out wrong ran to the end or took the server with it. Now
a job carries an Event: the console can raise it, the pipeline asks before
each stage and before each episode, and a stop is recorded as interrupted
rather than failed - a refusal is not a fault.

A process that dies cannot write its own epitaph. The stages it was
running stay marked running for ever, and the console spins over work
nobody is doing - which is worse than no progress at all, because it
looks like progress. So the next boot finds them and settles them
honestly.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8", errors="replace")

if "stop_job" in s:
    print("server.py: 停止接口已存在，跳过")
    raise SystemExit(0)

# --------------------------------------------- 1. a job can be stopped ---
old_start = '''    def start_job(self, kind: str, fn) -> str:
        jid = uuid.uuid4().hex[:12]
        self.jobs[jid] = {"id": jid, "kind": kind, "status": "running",
                          "result": None, "error": None}

        def _wrap():
            try:
                res = fn()
                self.jobs[jid].update(status="done", result=res)
            except Exception as e:  # noqa: BLE001
                log.error("job %s failed: %s", jid, traceback.format_exc())
                self.jobs[jid].update(status="error", error=str(e)[:500])

        threading.Thread(target=_wrap, daemon=True).start()
        return jid'''
new_start = '''    def start_job(self, kind: str, fn) -> str:
        jid = uuid.uuid4().hex[:12]
        # The event is what makes a run stoppable: the thread runs the
        # pipeline, the pipeline asks between stages and between episodes,
        # and this is the thing they ask. Without it a plan that turns out
        # wrong has to run to the end.
        stop = threading.Event()
        self.jobs[jid] = {"id": jid, "kind": kind, "status": "running",
                          "result": None, "error": None, "stop": stop}

        def _wrap():
            try:
                res = fn(stop)
                self.jobs[jid].update(status="done", result=res)
            except Exception as e:  # noqa: BLE001
                log.error("job %s failed: %s", jid, traceback.format_exc())
                self.jobs[jid].update(status="error", error=str(e)[:500])
            finally:
                # the event is not JSON; the record is handed to the page
                self.jobs[jid].pop("stop", None)

        threading.Thread(target=_wrap, daemon=True).start()
        return jid

    def stop_job(self, jid: str) -> bool:
        """Ask a running job to stop. False when there is no such job."""
        j = self.jobs.get(jid)
        if not j:
            return False
        ev = j.get("stop")
        if ev is None:
            return False
        ev.set()
        return True

    def running_jobs(self) -> list[str]:
        return [k for k, v in self.jobs.items() if v.get("status") == "running"]'''
assert old_start in s, "start_job 锚点没找到"
s = s.replace(old_start, new_start, 1)

# the progress-reporting variant: same event, one more argument
old_prog = '''        jid = uuid.uuid4().hex[:12]
        self.jobs[jid] = {"id": jid, "kind": kind, "status": "running",
                          "result": None, "error": None, "progress": {}}

        def _wrap():
            def report(**kw):
                self.jobs[jid]["progress"].update(kw)
            try:
                res = fn(report)
                self.jobs[jid].update(status="done", result=res)
            except Exception as e:  # noqa: BLE001
                log.error("job %s failed: %s", jid, traceback.format_exc())
                self.jobs[jid].update(status="error", error=str(e)[:500])

        threading.Thread(target=_wrap, daemon=True).start()
        return jid'''
new_prog = '''        jid = uuid.uuid4().hex[:12]
        stop = threading.Event()
        self.jobs[jid] = {"id": jid, "kind": kind, "status": "running",
                          "result": None, "error": None, "progress": {},
                          "stop": stop}

        def _wrap():
            def report(**kw):
                self.jobs[jid]["progress"].update(kw)
            try:
                res = fn(report, stop)
                self.jobs[jid].update(status="done", result=res)
            except Exception as e:  # noqa: BLE001
                log.error("job %s failed: %s", jid, traceback.format_exc())
                self.jobs[jid].update(status="error", error=str(e)[:500])
            finally:
                # the event is not JSON; the record is handed to the page
                self.jobs[jid].pop("stop", None)

        threading.Thread(target=_wrap, daemon=True).start()
        return jid'''
assert old_prog in s, "start_job_progress 锚点没找到"
s = s.replace(old_prog, new_prog, 1)

# -------------------------------------------------- 2. the POST route ---
old_route = '''            if path == "/api/run":
                return self._json(self._api_run(body))'''
new_route = '''            if path == "/api/run":
                return self._json(self._api_run(body))
            if path == "/api/jobs/stop":
                return self._json(self._api_jobs_stop(body))'''
assert old_route in s, "/api/run 路由锚点没找到"
s = s.replace(old_route, new_route, 1)

# ----------------------------------------------- 3. the stop endpoint ---
anchor = "        def _api_run(self, body: dict) -> dict:"
assert anchor in s, "_api_run 定义锚点没找到"
stop_ep = '''        def _api_jobs_stop(self, body: dict) -> dict:
            """Ask a running job to stop.

            The pipeline asks before each stage and before each episode,
            so this takes effect at the next item rather than at the end -
            which is the whole point of asking.
            """
            jid = str(body.get("job") or "").strip()
            if not jid:
                # no id: stop whatever is running. A console that can only
                # stop a job it knows the id of cannot stop anything,
                # because the page that submitted it may be closed.
                running = state.running_jobs()
                if not running:
                    return {"ok": False, "error": "没有正在运行的任务"}
                stopped = [j for j in running if state.stop_job(j)]
                return {"ok": True, "jobs": stopped,
                        "message": f"已请求停止 {len(stopped)} 个任务"}
            if state.stop_job(jid):
                return {"ok": True, "jobs": [jid], "message": "已请求停止"}
            return {"ok": False, "error": "没有这个任务，或它已经结束"}

'''
s = s.replace(anchor, stop_ep + anchor, 1)

p.write_text(s, encoding="utf-8")
print("server.py: 任务可停止了（stop_job + /api/jobs/stop）")
