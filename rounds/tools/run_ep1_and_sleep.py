"""The first episode, and then the machine goes off.

The run is the tail of the pipeline: the pictures and the clips, the
subtitles, the music, the check, the film, the report.  When it is
over - whether it worked or not - the machine is put to sleep, because
nobody is going to watch it tonight.

The outcome is written down before the machine goes, so the morning
starts with an answer and not with a question.
"""
import datetime
import json
import logging
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, r"E:\dramakit")

logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s",
                    stream=sys.stdout)

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline import make_context, run_pipeline  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

SLUG = "我死后-仙尊追悔莫及"
STAGES = ["visual", "lipsync", "subtitle", "music", "precheck", "compose", "qc"]
LOG = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\ep1_run.log")
STATUS = pathlib.Path(r"E:\dramakit\projects") / SLUG / "第1集出片状态.txt"

cfg = Config.load(Config.discover())
cfg.pipeline.only_episodes = [1]
store = ProjectStore.open(r"E:\dramakit\projects\%s" % SLUG)
ctx = make_context(cfg, store)

t0 = time.time()
res = {}
err = ""
try:
    res = run_pipeline(ctx, stages=STAGES)
except Exception as e:  # noqa: BLE001
    import traceback
    err = traceback.format_exc()
    logging.error("跑完了，但是出错了：%s" % e)

minutes = (time.time() - t0) / 60
proj = store.load()
ep = next((e for e in proj.episodes if e.index == 1), None)
shots = [sh for sc in (ep.scenes if ep else []) for sh in sc.shots]
n_img = sum(1 for sh in shots if sh.image_path)
n_vid = sum(1 for sh in shots if sh.video_path)
film = str(ctx.store.abs(ctx.store.episode_video_path(ep))) if ep else ""

lines = [
    "第1集出片 %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "用了 %.1f 分钟" % minutes,
    "镜头 %d，有图 %d，有视频 %d" % (len(shots), n_img, n_vid),
    "成片：%s" % (film or "**没有**"),
    "",
]
for k, v in res.items():
    lines.append("%-22s %s" % (k, str(v)[:200]))
if err:
    lines += ["", "出错：", err[-2000:]]
STATUS.write_text("\n".join(lines), encoding="utf-8")
with LOG.open("a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))

# the machine goes off
print("  关机：还有一分钟，机器就关了。")
subprocess.run(["shutdown", "/s", "/t", "60", "/c",
                 "第1集出片结束，机器自动关机"])
