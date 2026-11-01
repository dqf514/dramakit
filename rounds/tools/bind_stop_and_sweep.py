"""Hand the stop event to the run, and settle what a dead process left.

Three wirings. The event the endpoint raises has to reach the pipeline
that is meant to notice it, so execute() takes it and the context binds
it - without that the stop button raises a flag nothing reads. The
progress-reporting job gained the same argument when it gained the event,
and its one caller has to accept it. And a process that dies cannot mark
its own stages interrupted, so the next boot finds them still running and
settles them, rather than the console spinning over work nobody is doing.
"""
from pathlib import Path

# --------------------------------------------------- 1. actions 透传 ----
a = Path(r"E:\\dramakit\\dramakit\\ai\\actions.py")
t = a.read_text(encoding="utf-8", errors="replace")

if "stop_event" not in t:
    old_exec = '''def execute(action: Action, cfg: Config, *, projects_root="projects",
            catalog=None) -> dict:'''
    new_exec = '''def execute(action: Action, cfg: Config, *, projects_root="projects",
            catalog=None, stop_event=None) -> dict:'''
    assert old_exec in t, "execute 签名锚点没找到"
    t = t.replace(old_exec, new_exec, 1)

    old_call = '''    if kind == "run_pipeline":
        return _do_run(cfg, store, p)'''
    new_call = '''    if kind == "run_pipeline":
        return _do_run(cfg, store, p, stop_event=stop_event)'''
    assert old_call in t, "run_pipeline 分支锚点没找到"
    t = t.replace(old_call, new_call, 1)

    old_do = '''def _do_run(cfg: Config, store: ProjectStore, p: dict) -> dict:'''
    new_do = '''def _do_run(cfg: Config, store: ProjectStore, p: dict,
            stop_event=None) -> dict:'''
    assert old_do in t, "_do_run 签名锚点没找到"
    t = t.replace(old_do, new_do, 1)

    # bind it into the context the pipeline runs on
    old_ctx = '''    ctx = make_context(cfg, store)
    res = run_pipeline(ctx, stages=stages, season=season)'''
    new_ctx = '''    ctx = make_context(cfg, store)
    if stop_event is not None:
        # the pipeline asks this between stages and between episodes
        ctx.bind_stop(stop_event)
    res = run_pipeline(ctx, stages=stages, season=season)'''
    assert old_ctx in t, "make_context 调用锚点没找到"
    t = t.replace(old_ctx, new_ctx, 1)

    a.write_text(t, encoding="utf-8")
    print("actions.py: stop_event 透传到 Context")
else:
    print("actions.py: stop_event 已存在")

# ------------------------------------------------- 2. server 的两个 _job --
s = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
sv = s.read_text(encoding="utf-8", errors="replace")

if "stop_event=stop" not in sv:
    # the AI-run job
    old_ai = '''            def _job():
                res = actions.execute(act, state.cfg,
                                      projects_root=state.projects_root,
                                      catalog=state.catalog)'''
    new_ai = '''            def _job(stop):
                res = actions.execute(act, state.cfg,
                                      projects_root=state.projects_root,
                                      catalog=state.catalog,
                                      stop_event=stop)'''
    n = sv.count(old_ai)
    sv = sv.replace(old_ai, new_ai)
    print(f"server.py: _api_ai_run 等 {n} 处 _job 接上 stop")

    # the plain run job
    old_run = '''            def _job():
                res = actions.execute(act, state.cfg,
                                      projects_root=state.projects_root,
                                      catalog=state.catalog)'''
    # (already replaced above if identical; find any remaining)
    if old_run in sv:
        sv = sv.replace(old_run, new_ai)

    # nodes_sync: its caller now passes two arguments
    old_sync = "            def _job(report_progress):"
    new_sync = "            def _job(report_progress, stop):"
    if old_sync in sv:
        sv = sv.replace(old_sync, new_sync, 1)
        print("server.py: nodes_sync 的 _job 接受 stop")

    s.write_text(sv, encoding="utf-8")
else:
    print("server.py: stop_event 已接上")

# ----------------------------------------- 3. 启动时清理残留的 running ----
sv = s.read_text(encoding="utf-8", errors="replace")

if "_settle_leftover_runs" not in sv:
    # the sweeper, as a State method
    anchor = "    def running_jobs(self) -> list[str]:"
    assert anchor in sv, "running_jobs 锚点没找到"
    sweeper = '''    def settle_leftover_runs(self) -> int:
        """Mark the stages a dead process left claiming to run.

        A process that dies cannot write its own epitaph: the stage it was
        working on stays running for ever, and the console spins over work
        nobody is doing - which is worse than no progress, because it looks
        like progress. The next boot finds them and says what happened.
        """
        settled = 0
        for slug in self.project_slugs():
            store = self.open_store(slug)
            if store is None:
                continue
            try:
                proj = store.load()
            except Exception:  # noqa: BLE001
                continue
            changed = False
            for stage, st in list(proj.stage_status.items()):
                if st == Status.RUNNING:
                    proj.stage_status[stage] = Status.INTERRUPTED
                    changed = True
                    settled += 1
            for ep in proj.episodes:
                for stage, st in list((ep.stage_status or {}).items()):
                    if st == Status.RUNNING:
                        ep.stage_status[stage] = Status.INTERRUPTED
                        changed = True
                        settled += 1
            for season in (proj.seasons or []):
                for stage, st in list((season.stage_status or {}).items()):
                    if st == Status.RUNNING:
                        season.stage_status[stage] = Status.INTERRUPTED
                        changed = True
                        settled += 1
            if changed:
                store.save(proj)
                log.warning("项目 %s: 有阶段停在 running，已标记为中断", slug)
        if settled:
            log.warning("启动清理：%d 个阶段原为 running，已标记为中断", settled)
        return settled

''' + anchor
    sv = sv.replace(anchor, sweeper, 1)

    # call it when the server comes up
    old_serve = "    state = State(cfg, config_path, projects_root)"
    new_serve = '''    state = State(cfg, config_path, projects_root)
    # a process that died could not say so; settle what it left running
    # before anyone reads the console and believes it
    state.settle_leftover_runs()'''
    assert old_serve in sv, "serve 里 state 创建锚点没找到"
    sv = sv.replace(old_serve, new_serve, 1)

    s.write_text(sv, encoding="utf-8")
    print("server.py: 启动时清理残留的 running 状态")
else:
    print("server.py: 启动清理已存在")
