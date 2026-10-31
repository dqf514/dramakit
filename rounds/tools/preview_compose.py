"""Compose a preview from whatever is rendered.

The whole chain after the videos - the timeline, the colour grade, the
voice that comes out of the picture, the music bed, the mix, the subtitles
burned in, the AI declaration - can be tested on a copy of the project
while the rest of the episodes is still being drawn.  The shots that are
not ready fall back to their still, which is what compose does anyway.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.compose import compose_episode
from dramakit.project import ProjectStore

SRC = Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
DST = Path(r"C:\\tmp\\preview")

if DST.exists():
    shutil.rmtree(DST, ignore_errors=True)
DST.mkdir(parents=True, exist_ok=True)
for sub in ("project.json", "source", "images", "characters", "locations",
            "audio", "video", "music", "subs"):
    s = SRC / sub
    if not s.exists():
        continue
    if s.is_file():
        shutil.copy2(s, DST / sub)
    else:
        shutil.copytree(s, DST / sub, dirs_exist_ok=True)
print("拷贝到", DST)

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(DST)
ctx = Context(cfg, store)
ep = ctx.project.episode(1)
have = sum(1 for sc in ep.scenes for sh in sc.shots if sh.video_path)
print(f"第1集: {ep.total_shots} 个片段，其中 {have} 个已经有视频")

out = compose_episode(ctx, ep)
print("成片:", out)
r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                    "stream=codec_type,codec_name,width,height,duration",
                    "-of", "default=noprint_wrappers=1", out],
                   capture_output=True, text=True)
print(r.stdout)
