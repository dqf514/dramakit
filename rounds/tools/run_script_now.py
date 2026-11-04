"""Run the script stage on this project, and watch it.

The stage reported "episodes_scripted: 0" and finished inside a
second, so it never reached the model.  This runs it with the log in
front of us.
"""
import logging
import sys

sys.path.insert(0, r"E:\dramakit")

logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s",
                    stream=sys.stdout)

from dramakit.config import Config
from dramakit.pipeline import script as script_stage
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
store = ProjectStore.open(r"E:\dramakit\projects\魔兽永恒之树")
ctx = Context(cfg, store)
print("target_episodes:", [(e.index, len(e.scenes)) for e in ctx.target_episodes()])
print("only_episodes:", cfg.pipeline.only_episodes)
res = script_stage.run(ctx)
print("结果:", res)
for ep in ctx.target_episodes():
    print(f"第{ep.index}集《{ep.title}》 {len(ep.scenes)} 场 "
          f"{ep.total_shots} 镜  状态={ep.status.value}")
    for sc in ep.scenes:
        print(f"   【{sc.location}·{sc.time_of_day}】{sc.summary}")
        for l in sc.lines:
            print(f"      {l.speaker}（{l.emotion}）: {l.text}")
