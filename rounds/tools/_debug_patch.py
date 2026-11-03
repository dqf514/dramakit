"""Remove the debug lines left in the source while chasing a failure."""
import pathlib

targets = {
    r"E:\dramakit\dramakit\pipeline\runner.py": [
        "    print('DEBUG run_pipeline called, ctx=', id(ctx), flush=True)\n",
        "    import traceback\n"
        "    log.warning('DEBUG run_pipeline 被调用，调用栈:\\n%s',\n"
        "                ''.join(traceback.format_stack()[-6:]))\n",
    ],
    r"E:\dramakit\dramakit\ai\actions.py": [
        "    print('DEBUG _do_run calling run_pipeline, ctx=', id(ctx), flush=True)\n",
    ],
    r"E:\dramakit\dramakit\web\server.py": [
        '            log.warning("DEBUG _api_run 启动任务 slug=%s", act.params.get("project"))\n',
        '            log.warning("DEBUG _api_run 任务号=%s 现有任务=%s", jid, list(state.jobs.keys()))\n',
    ],
}

for path, lines in targets.items():
    p = pathlib.Path(path)
    t = p.read_text(encoding="utf-8")
    for line in lines:
        if line in t:
            t = t.replace(line, "")
            print("removed from", p.name, "->", line.strip()[:60])
    p.write_text(t, encoding="utf-8")

# anything left that looks like a debug leftover
for path in targets:
    p = pathlib.Path(path)
    for i, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
        if "DEBUG" in line and "log.debug" not in line:
            print("LEFT", p.name, i, line.strip()[:90])
print("done")
