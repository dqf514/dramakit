"""Only draw the shots that have something to draw with.

The picture stage is now called repeatedly while the writers are still
going, so it has to leave the shots whose prompts do not exist yet alone
rather than trying to render them. A shot is ready when the still model
has a prompt for it, and for the clip when the video model does - which
is the same prompt when only one has been written.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")

if "not shot.prompt" in s:
    print("visual.py: 已有就绪判断，跳过")
    raise SystemExit(0)

old = '''        for sc in ep.scenes:
            for shot in sc.shots:
                if shot.status == Status.DONE and shot.has_visual:
                    continue
                jobs.append((ep, sc, shot))'''
new = '''        for sc in ep.scenes:
            for shot in sc.shots:
                if shot.status == Status.DONE and shot.has_visual:
                    continue
                # A shot is drawn when that shot is ready, not when the
                # project is: the stage is called while the writers are
                # still going, and a shot with no prompt yet has nothing to
                # be drawn from. It is picked up on a later pass.
                if do_image and not (shot.prompt or "").strip():
                    continue
                if do_video and not (shot.video_prompt or "").strip():
                    continue
                jobs.append((ep, sc, shot))'''
assert old in s, "jobs 构建锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("visual.py: 跳过还没写好提示词的镜头，等下一趟")
