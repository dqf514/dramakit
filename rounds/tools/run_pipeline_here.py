"""Run the pipeline here, and say what it is doing.

The console holds the pipeline in memory, and this machine's console is
running as an administrator - so a change to the code is not in effect
there until it is restarted, and it cannot be restarted from here.  So
the run happens here instead: the same stages, the same context, the
same code on disk.

The log goes to a file, in UTF-8, because the console on this machine
re-encodes it and turns every Chinese character into noise.
"""
import logging
import pathlib
import sys
import time

sys.path.insert(0, r"E:\dramakit")

LOG = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\stage_run.log")
_fh = LOG.open("w", encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(_fh)], force=True)

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline import make_context, run_pipeline  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

SLUG = sys.argv[1]
STAGES = sys.argv[2].split(",")
EPISODES = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else []

cfg = Config.load(Config.discover())
if EPISODES:
    cfg.pipeline.only_episodes = EPISODES
store = ProjectStore.open(r"E:\dramakit\projects\%s" % SLUG)
ctx = make_context(cfg, store)

t0 = time.time()
res = run_pipeline(ctx, stages=STAGES)
out = ["用了 %.1f 分钟" % ((time.time() - t0) / 60)]
for k, v in res.items():
    out.append("%-22s %s" % (k, str(v)[:200]))
_fh.write("\n" + "\n".join(out) + "\n")
_fh.flush()
print("\n".join(out))
