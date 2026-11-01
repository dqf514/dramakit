"""The run's own log, where a person can read it.

The pipeline already says what it is doing - which episode, which shot,
which provider refused, what it gave up on - in a hundred and eleven
places. All of it was thrown away: nothing configured a handler, so INFO
fell to the last-resort handler and vanished, which is also why the log
file was empty. The work was being described to nobody.

So the logger keeps the last of its lines in memory and the console shows
them. The stages are not touched: they already log through one logger, so
a handler on that logger is enough, and a line written for a debugging
session becomes a line a user can act on.

The tail is a fixed-size deque, so a run that logs for days holds the
last few hundred lines and nothing more.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

if "class LogTail" in s:
    print("server.py: 日志尾巴已存在，跳过")
    raise SystemExit(0)

# ------------------------------------------------- 1. the ring buffer ---
anchor = "class State:"
assert anchor in s, "找不到 State"
tail_cls = '''class LogTail(logging.Handler):
    """The last few hundred log lines, kept in memory for the console.

    The pipeline logs what it is doing - the episode it is on, the shot it
    is drawing, the call that refused - through one logger. Nothing was
    reading it, because nothing configured a handler and INFO fell through
    to the last-resort handler and out of the process. A handler here is
    enough: the same lines written for a debugging session are the lines a
    user needs to know that episode 37 is where the run is stuck.

    A deque with a fixed maxlen, so a run that logs for a week holds the
    last few hundred lines and no more.
    """

    def __init__(self, capacity: int = 800):
        super().__init__(level=logging.INFO)
        self.lines: "deque[dict]" = collections.deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.lines.append({
                "t": record.created,
                "lv": record.levelname[:1].lower(),
                "msg": record.getMessage(),
            })
        except Exception:  # noqa: BLE001 - a log handler must never raise
            pass

    def tail(self, n: int = 120) -> list[dict]:
        if n <= 0:
            return list(self.lines)
        return list(self.lines)[-n:]


''' + anchor
s = s.replace(anchor, tail_cls, 1)

# collections is needed
if "\nimport collections" not in s:
    s = s.replace("import json\n", "import collections\nimport json\n", 1)

# ------------------------------------------------ 2. it lives on state --
old_ctor = '''        self.jobs: dict[str, dict] = {}
        self._brain = None'''
new_ctor = '''        self.jobs: dict[str, dict] = {}
        self._brain = None
        # what the run is saying, for the panel to show
        self.log_tail = LogTail()'''
assert old_ctor in s, "State.__init__ 锚点没找到"
s = s.replace(old_ctor, new_ctor, 1)

# -------------------------------------------- 3. attach it at startup ---
old_serve = '''    state = State(cfg, config_path, projects_root)'''
new_serve = '''    state = State(cfg, config_path, projects_root)
    # The stages log through the package logger and nobody was listening:
    # with no handler, INFO falls to the last-resort handler and is lost,
    # which is why the log file was empty while a run was going. One
    # handler on the package logger captures every stage without touching
    # any of them, and `dramakit.web` reaches it by propagation.
    logging.getLogger("dramakit").addHandler(state.log_tail)
    logging.getLogger("dramakit").setLevel(logging.INFO)'''
assert old_serve in s, "serve 里 state 创建锚点没找到"
s = s.replace(old_serve, new_serve, 1)

# --------------------------------------------------- 4. the endpoint ----
old_route = '''            if path == "/api/jobs":'''
new_route = '''            if path == "/api/logs":
                n = (query.get("n") or ["120"])[0]
                try:
                    n = int(n)
                except ValueError:
                    n = 120
                return self._json({"ok": True, "lines": state.log_tail.tail(n)})
            if path == "/api/jobs":'''
assert old_route in s, "/api/jobs 路由锚点没找到"
s = s.replace(old_route, new_route, 1)

p.write_text(s, encoding="utf-8")
print("server.py: 日志进内存了（LogTail + /api/logs）")
