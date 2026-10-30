"""How many segments an episode gets, and how long they are.

The format says five minutes per episode and a segment is six to fifteen
seconds, so an episode is about thirty segments.  The material decides how
many of them carry a line: a scene with five lines does not get thirty
segments of picture, it gets the few it can hold plus the reactions and
inserts that make them breathe.

The segments are then scaled so that they add up to the length of the
episode, which is what the episode was supposed to be in the first place.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\storyboard.py")
s = p.read_text(encoding="utf-8")

old = """        dialogue_need = sum(needs)
        # The episode has a length to hit - five minutes - and a segment is
        # six to fifteen seconds, so the episode needs about thirty of them.
        # The number of segments is decided by the length of the episode and
        # by the dialogue it has to hold, whichever asks for more.
        target = float(ep.duration_target or cfg.segment.episode_duration)
        avg = (dmin + dmax) / 2.0
        length_need = max(1, int(round(target / avg)))
        total_need = max(dialogue_need, length_need)
        for sc, need in zip(ep.scenes, needs):
            if sc.shots:
                continue
            share = max(cfg.min_shots_per_scene,
                        -(-need * total_need // max(dialogue_need, 1)))
            sc._shot_budget = min(share, cfg.max_shots_per_scene)"""

new = """        dialogue_need = sum(needs)
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
        total_need = length_need
        for sc, need in zip(ep.scenes, needs):
            if sc.shots:
                continue
            share = max(cfg.min_shots_per_scene,
                        -(-need * total_need // max(dialogue_need, 1)))
            sc._shot_budget = min(share, cfg.max_shots_per_scene)"""

assert old in s, "分镜预算锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("storyboard.py: 片段预算按一集 5 分钟来算")

# and the prompt tells the model how the lines are spread out
p2 = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
t = p2.read_text(encoding="utf-8")
old2 = """- **这一集总共约 {{episode_seconds}} 秒**，一个片段 {{dur_min}}~{{dur_max}} 秒，
  平均每个片段约 {{avg_seconds}} 秒。请按这个密度给片段排长度，
  让本场加起来的时长贴近本集在全片中占的那一份"""
new2 = """- **这一集总共约 {{episode_seconds}} 秒**，一个片段 {{dur_min}}~{{dur_max}} 秒，
  平均每个片段约 {{avg_seconds}} 秒。请按这个密度给片段排长度，
  让本场加起来的时长贴近本集在全片中占的那一份
- **台词要摊开，不要全堆在头几个片段**：本场的台词要分给大部分片段，
  平均每个片段一两句话就够。剩下的时间给表演、对方的反应、
  道具的插入特写和空镜——**片段比台词长出来的那部分是有内容的，不是空白**"""
assert old2 in t, "提示词锚点没找到"
t = t.replace(old2, new2, 1)
p2.write_text(t, encoding="utf-8")
print("templates.py: 台词摊开的要求写进去了")
