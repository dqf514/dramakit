import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import Shot
from dramakit.pipeline.visual import _shot_frames


class FakeCtx:
    def __init__(self, cfg):
        self.cfg = cfg


c = Config.load(r"E:\dramakit\config\default.yaml")
ctx = FakeCtx(c)
print(f"frame_mode={c.comfyui.frame_mode} fps={c.comfyui.fps} "
      f"max={c.comfyui.max_video_seconds}s")
for d in (2.0, 3.2, 5.0, 6.5, 8.0, 10.0, 12.0, 15.0, 20.0):
    f = _shot_frames(ctx, Shot(id="x"), d)
    print(f"  {d:5.1f}s -> {f:4d} 帧 = {f/24:.2f}s")
