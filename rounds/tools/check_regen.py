"""Check that re-rendering a shot from the console works.

The failure was a name that did not exist, raised while the arguments
were being worked out - so the clip was never even asked for. That is
worth checking properly rather than by eye: the function is called with
the video step replaced by one that only records what it was given, so
nothing is rendered and the answer is about the call, not about the
card.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.project import ProjectStore
from dramakit.pipeline import visual as V

PROJ = Path(r"E:\dramakit\projects\星际骷髅兵")
cfg = Config.load(Config.discover())
store = ProjectStore.open(PROJ)

called = {}


def fake_video(ctx, sc, shot, duration=0.0, ep=None):
    called["shot"] = shot.id
    called["episode"] = getattr(ep, "index", None)
    called["duration"] = duration
    return shot.id, True, ""


def fake_image(ctx, sc, shot):
    called["image"] = shot.id
    return shot.id, True, ""


V._gen_video = fake_video
V._gen_image = fake_image

# the first shot of the first episode that has a picture
proj = store.load()
target = None
for ep in proj.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if sh.image_path and (PROJ / sh.image_path).exists():
                target = (ep.index, sh.id)
                break
        if target:
            break
    if target:
        break

if not target:
    print("  找不到可用的镜头")
    raise SystemExit(1)

ep_index, shot_id = target
print(f"  试着重生成：第 {ep_index} 集 / {shot_id}")

res = V.regen_shot(store, cfg, ep_index, shot_id, mode="all")
print("  返回:", {k: v for k, v in res.items() if k in ("ok", "shot", "error")})
print("  视频那一步收到:", called.get("shot"), "| 集:", called.get("episode"),
      "| 时长:", called.get("duration"))
if called.get("episode") != ep_index:
    print("  **传错了集**")
    raise SystemExit(1)
print("  ✓ 名字对上了，剧集也对上了")
