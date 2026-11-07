"""Run the pipeline here, and say what it is doing.

The console holds the pipeline in memory, and this machine's console is
running as an administrator - so a change to the code is not in effect
there until it is restarted, and it cannot be restarted from here.  So
the run happens here instead: the same stages, the same context, the
same code on disk.
"""
import logging
import sys
import time

sys.path.insert(0, r"E:\dramakit")

logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s",
                    stream=sys.stdout)

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
print("  项目 %s   阶段 %s   集 %s" % (SLUG, STAGES, EPISODES or "全部"))

t0 = time.time()
res = run_pipeline(ctx, stages=STAGES)
print("  用了 %.1f 分钟" % ((time.time() - t0) / 60))
for k, v in res.items():
    print("    %-22s %s" % (k, str(v)[:160]))
