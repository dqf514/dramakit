"""A run that can be stopped, and a stage that admits it was stopped.

Three things were impossible. A submitted run could not be stopped at all
- the job lived in a daemon thread with no flag anyone could raise, so a
plan that turned out wrong had to run for days or take the server down
with it. A stage that had been interrupted went on claiming it was
running, because the process died before it could say otherwise, and the
console spun for ever over work nobody was doing. And nothing could begin
at a chosen episode, so the only way to make ten of them was to make all
of them first.

This adds the stop: a job carries an Event, the pipeline asks before each
stage and inside the loops that cost time, and a stopped run marks its
stage interrupted rather than failed - a refusal is not a fault.

The interrupted state is also swept on startup. A process that dies cannot
write its own epitaph, so the next boot finds the stages still marked
running and settles them honestly.
"""
from pathlib import Path

# ------------------------------------------------------------ 1. Status ---
p = Path(r"E:\\dramakit\\dramakit\\models.py")
s = p.read_text(encoding="utf-8", errors="replace")

if "INTERRUPTED" not in s:
    old = '''class Status(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"'''
    new = '''class Status(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    # a run that was asked to stop, or that a restarting process left
    # behind. Not a fault: the stage did not fail, it was interrupted -
    # and saying so is what lets a resume begin at the right place.
    INTERRUPTED = "interrupted"'''
    assert old in s, "Status 枚举锚点没找到"
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("models.py: 加了 Status.INTERRUPTED")
else:
    print("models.py: INTERRUPTED 已存在")

# ------------------------------------------------- 2. Context 可被叫停 ---
b = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
t = b.read_text(encoding="utf-8", errors="replace")

if "def check_stop" not in t:
    old_ctx = '''    def __init__(self, cfg: Config, store: ProjectStore,
                 providers: Optional[Providers] = None):
        self.cfg = cfg
        self.store = store
        self.providers = providers or Providers(cfg, store.root)
        self.project: Project = store.load()
        self.log: logging.Logger = logging.getLogger("dramakit")'''
    new_ctx = '''    def __init__(self, cfg: Config, store: ProjectStore,
                 providers: Optional[Providers] = None):
        self.cfg = cfg
        self.store = store
        self.providers = providers or Providers(cfg, store.root)
        self.project: Project = store.load()
        self.log: logging.Logger = logging.getLogger("dramakit")
        # set when someone asks the run to stop. Stages that loop over
        # many episodes or many calls ask between items, so a stop lands
        # in seconds rather than at the end of the batch.
        self._stop = None'''
    assert old_ctx in s or old_ctx in t, "Context.__init__ 锚点没找到"
    t = t.replace(old_ctx, new_ctx, 1)

    # the asking, and the raising
    anchor = "    def save(self) -> None:\n        self.store.save(self.project)"
    assert anchor in t, "Context.save 锚点没找到"
    add = '''    def bind_stop(self, event) -> None:
        """Hand the run the thing that can stop it."""
        self._stop = event

    @property
    def stopped(self) -> bool:
        return bool(self._stop is not None and self._stop.is_set())

    def check_stop(self) -> None:
        """Raise if someone asked the run to stop.

        Stages call this between the items that cost time - an episode, a
        shot, an API call - so that asking to stop takes effect now rather
        than after the batch. A stop is not a failure, so it raises its
        own error and the runner records it as interrupted.
        """
        if self.stopped:
            raise RunStopped()

''' + anchor
    t = t.replace(anchor, add, 1)

    # the exception, near the top after imports
    imp = "from ..providers import Providers"
    if "class RunStopped" not in t:
        k = t.find(imp)
        assert k > 0, "找不到 providers 导入行"
        t = t[:k] + '''class RunStopped(Exception):
    """Raised when a run is asked to stop. Not a fault - a refusal."""


''' + t[k:]
    b.write_text(t, encoding="utf-8")
    print("base.py: Context 能被叫停了（bind_stop / stopped / check_stop）")
else:
    print("base.py: check_stop 已存在")
