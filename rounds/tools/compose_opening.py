"""The film, and the fifteen seconds of it.

The episode is put together the way the pipeline puts it together -
picture, voice, subtitles, music - and then the first fifteen seconds
are cut out of it, because that is what was asked for.
"""
import logging
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, r"E:\dramakit")

logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s",
                    stream=sys.stdout)

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline import make_context  # noqa: E402
from dramakit.pipeline import compose as compose_stage  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

DST = r"C:\Users\David\AppData\Local\Temp\opencode\opening_test"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode")

cfg = Config.load(Config.discover())
store = ProjectStore.open(DST)
ctx = make_context(cfg, store)
ep = store.load().episodes[0]

t0 = time.time()
path = compose_stage.compose_episode(ctx, ep)
print("  成片：%s（%.1f 分钟）" % (path, (time.time() - t0) / 60))

# how long is it, and what is the first fifteen seconds of it?
probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True, encoding="utf-8")
print("  时长：%s 秒" % probe.stdout.strip())

cut = OUT / "opening_15s.mp4"
r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-t", "15",
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    "-c:a", "aac", str(cut)], capture_output=True, text=True,
                   encoding="utf-8")
print("  十五秒：%s（%s）" % (cut, r.stderr.strip()[:120] or "好"))
