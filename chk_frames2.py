import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.pipeline.visual import _shot_frames


class F:
    pass


class C:
    pass


c = C()
c.cfg = F()
c.cfg.comfyui = F()
c.cfg.comfyui.frame_mode = "auto"
c.cfg.comfyui.fps = 24
c.cfg.comfyui.max_video_seconds = 15.0
c.cfg.comfyui.frames = 124

for d in (2.0, 2.4, 2.8, 3.2, 3.5, 4.0, 5.0, 8.0, 15.0):
    f = _shot_frames(c, None, d)
    ok = "够长(只裁切)" if f / 24 >= d else "偏短(会定格)"
    print(f"  槽位 {d:5.1f}s -> {f:4d} 帧 = {f/24:5.2f}s  {ok}")
