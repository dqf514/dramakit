"""The director decides the length; the model decides what it can do.

Two rules were written into the code that were never ours to write:

  * the segments of an episode were scaled so that they add up to exactly
    the target length, and
  * the number of segments was worked out from the length of the dialogue.

Both are the director's business.  What is not the director's business is
what the video model can make: MiniMax H3 generates between about five
and fifteen seconds of picture in one go, and a segment outside that range
cannot be rendered at all.  So the range stays - it is the machine's
limit - and inside it the length is the director's call, and the episode is
as long as the segments add up to.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")


def patch(path: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s and old not in s:
            print(f"  {path}: 已经打过补丁了")
            continue
        assert old in s, f"{path}: 锚点没找到\n{old[:200]}"
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  {path}: 改好了")


# --------------------------------------------------------------------------- #
# 1. the storyboard: the director's lengths, the model's range
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/storyboard.py", [
    # the budget: a hint for the model, not a formula
    ("""        dialogue_need = sum(needs)
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
        target = min(spec, total_need * dmax)""",
     """        dialogue_need = sum(needs)
        # How many segments the episode wants is the director's business.
        # The dialogue says how many it needs to hold the lines; the format
        # says roughly how long the episode should be; the model says how
        # long a segment may be.  The director is told all three and the
        # number of segments is not worked out for them.
        avg = (dmin + dmax) / 2.0
        spec = float(ctx.cfg.segment.episode_duration)
        length_need = max(1, int(round(spec / avg)))
        cap = max(cfg.min_shots_per_scene * len(ep.scenes),
                  int(dialogue_need * 2.5))
        total_need = min(max(dialogue_need, length_need), cap)
        target = min(spec, total_need * dmax)
        episode_seconds = int(spec)"""),
    # the segments are not scaled to a target any more
    ("""        # the segments of the episode are scaled so that they fill it
        _fit_durations([sh for sc in ep.scenes for sh in sc.shots],
                       target, dmin, dmax)
        ctx.mark(ep, "storyboard", Status.DONE)""",
     """        # The lengths are the director's.  They are only kept inside the
        # range the video model can render - a segment outside it cannot be
        # made at all.
        for sc in ep.scenes:
            for sh in sc.shots:
                sh.duration = round(max(dmin, min(dmax, float(sh.duration or dmin))), 2)
        ctx.mark(ep, "storyboard", Status.DONE)"""),
    # the prompt is told the episode's length is a suggestion
    ("""                            episode_seconds=int(target),
                            avg_seconds=round(avg, 1),""",
     """                            episode_seconds=episode_seconds,
                            avg_seconds=round(avg, 1),"""),
])

# --------------------------------------------------------------------------- #
# 2. the prompt: the length is the director's call
# --------------------------------------------------------------------------- #
patch("dramakit/prompts/templates.py", [
    ("""- duration: 该片段秒数（{{dur_min}}~{{dur_max}}秒；一个片段里可以有好几个镜头，
  视频模型会在片段内部按你写的切点切）""",
     """- duration: 该片段秒数（{{dur_min}}~{{dur_max}} 秒；这是**模型一次能生成的画面长度**，
  在这个范围之内由你按戏来定：一句短台词可能只要两三秒，一个沉默的反应可能要给十秒，
  一场戏的关键一刻值得慢慢给。一个片段里可以有好几个镜头，
  视频模型会在片段内部按你写的切点切）"""),
    ("""- **这一集总共约 {{episode_seconds}} 秒**，一个片段 {{dur_min}}~{{dur_max}} 秒，
  平均每个片段约 {{avg_seconds}} 秒。请按这个密度给片段排长度，
  让本场加起来的时长贴近本集在全片中占的那一份""",
     """- **这一集大约 {{episode_seconds}} 秒（这是个参考，不是硬指标）**。
  一集三到六分钟都成立，**跟着剧情的节奏走**：哪里戏重，哪里就给时间；
  哪里是过场，哪里就一带而过。片段的长度你定，定完这一集自然就是这个长度"""),
])

# --------------------------------------------------------------------------- #
# 3. the config: the range is the model's range
# --------------------------------------------------------------------------- #
patch("config/default.yaml", [
    ("""  shot_duration_range: [6.0, 15.0]            # 一个片段 6~15 秒，段里有多个镜头""",
     """  shot_duration_range: [5.0, 15.0]            # 视频模型一次能生成的画面长度（技术上限，不是导演规定）"""),
])
