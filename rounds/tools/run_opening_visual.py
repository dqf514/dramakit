"""Make the clips.

The stage does the two phases itself: the pictures first, then the
videos on the two 3090s.
"""
import logging
import sys
import time

sys.path.insert(0, r"E:\dramakit")

logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s",
                    stream=sys.stdout)

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline import make_context  # noqa: E402
from dramakit.pipeline import visual as visual_stage  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

DST = r"C:\Users\David\AppData\Local\Temp\opencode\opening_test"

cfg = Config.load(Config.discover())
store = ProjectStore.open(DST)
ctx = make_context(cfg, store)

t0 = time.time()
res = visual_stage.run(ctx)
print("  出图出视频：%s（%.1f 分钟）" % (res, (time.time() - t0) / 60))
for ep in store.load().episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            print("   %s  图=%s  视频=%s  %s秒"
                  % (sh.id[-6:], "有" if sh.image_path else "无",
                     "有" if sh.video_path else "无", sh.duration))
