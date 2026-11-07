"""The merged stage, on this book, for the first episode.

The writer and the director are one call now, so what comes out is the
lines and the shots together.  This runs that on episode one and shows
what the episode looks like: the scenes, the beats, the lines, and the
shots - with the coverage the shots have to have.
"""
import logging
import sys
import io

sys.path.insert(0, r"E:\dramakit")

REPORT = r"E:\dramakit\rounds\tools\_ep1_report.txt"
_buf = io.StringIO()


class _Tee(io.TextIOBase):
    def write(self, s):
        _buf.write(s)
        return len(s)

    def flush(self):
        pass


logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s",
                    stream=_Tee())

from dramakit.config import Config
from dramakit.pipeline import script as script_stage
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

PROJ = r"E:\dramakit\projects\穿成亿万总裁他前妻"

cfg = Config.load(Config.discover())
cfg.pipeline.only_episodes = [1]
store = ProjectStore.open(PROJ)
ctx = Context(cfg, store)
print("目标集:", [(e.index, len(e.scenes)) for e in ctx.target_episodes()])
print("题材:", ctx.project.art_direction.genre)

res = script_stage.run(ctx)
print("结果:", res)

for ep in ctx.target_episodes():
    print("")
    print("第%d集《%s》 %d 场 %d 镜" % (ep.index, ep.title,
                                       len(ep.scenes), ep.total_shots))
    for sc in ep.scenes:
        print("  【%s·%s】%s（%s）" % (sc.location, sc.time_of_day,
                                       sc.summary, sc.mood))
        print("    拍点 %d 个：" % len(sc.beats))
        for i, b in enumerate(sc.beats, 1):
            print("      %d. %s" % (i, b.action))
        print("    台词 %d 句：" % len(sc.lines))
        for i, l in enumerate(sc.lines, 1):
            print("      %d. %s（%s）: %s" % (i, l.speaker, l.emotion, l.text))
        print("    镜头 %d 个：" % len(sc.shots))
        for sh in sc.shots:
            print("      [%s/%s/%s/%s] %s秒  %s"
                  % (sh.shot_type.value, sh.angle, sh.height, sh.camera_move,
                     sh.duration, sh.action))
            print("         拍%s 台词%s 角色%s"
                  % (sh.beats, sh.line_indices, sh.characters))

with open(REPORT, "w", encoding="utf-8") as f:
    f.write(_buf.getvalue())
print("报告写到", REPORT)
