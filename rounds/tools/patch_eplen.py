"""How long an episode is, and how many segments it has.

The episode is as long as the format asks for - five minutes - and the
segments are fitted to it.  A scene that has little to say does not get
five minutes of picture: a scene with five lines in it gets the handful of
segments it can hold, and the episode it is in is shorter.

What used to happen: the length of the dialogue decided the length of the
episode, so an episode with a lot of talking came out at five minutes and
forty-six seconds, over the limit the format puts on it.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\storyboard.py")
s = p.read_text(encoding="utf-8")

old = """        dialogue_need = sum(needs)
        # The format asks for a five minute episode and a segment is six to
        # fifteen seconds, so an episode is about thirty of them.  What the
        # material can hold decides how many of them carry a line: a scene
        # with five lines does not get thirty segments of picture.
        avg = (dmin + dmax) / 2.0
        spec = float(ctx.cfg.segment.episode_duration)
        target = max(spec, dialogue_need * avg)
        length_need = max(dialogue_need, int(round(target / avg)))
        # a scene never gets more than two and a half times what its dialogue
        # can hold - the rest of the episode's length is the picture
        cap = max(cfg.min_shots_per_scene * len(ep.scenes),
                  int(dialogue_need * 2.5))
        length_need = min(length_need, cap)
        target = max(dialogue_need * avg, length_need * avg)
        total_need = length_need"""

new = """        dialogue_need = sum(needs)
        # The format asks for a five minute episode and a segment is six to
        # fifteen seconds, so an episode is about thirty of them.  What the
        # material can hold decides how many of them carry a line: a scene
        # with five lines does not get thirty segments of picture.
        avg = (dmin + dmax) / 2.0
        spec = float(ctx.cfg.segment.episode_duration)
        length_need = max(1, int(round(spec / avg)))
        # a scene never gets more than two and a half times what its dialogue
        # can hold - the rest of the episode's length is the picture
        cap = max(cfg.min_shots_per_scene * len(ep.scenes),
                  int(dialogue_need * 2.5))
        total_need = min(max(dialogue_need, length_need), cap)
        # the length of the episode follows from the segments: the format's
        # five minutes, and no more than the segments can carry
        target = min(spec, total_need * dmax)"""

assert old in s, "分镜预算锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("storyboard.py: 一集的长度由配置的时长和片段数共同决定")
