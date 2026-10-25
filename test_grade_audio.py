"""Reproduce the graded-clip audio mismatch and check the fix."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff
from dramakit.media import grade as gr

TMP = Path(r"C:\Users\David\AppData\Local\Temp\opencode\gradetest2")
TMP.mkdir(parents=True, exist_ok=True)

src = Path(r"E:\dramakit\projects\测试短剧\video\shot_sh-6db4be00.mp4")
plain = TMP / "plain.mp4"          # like normalize_video_clip: audio stripped
ff.normalize_video_clip(src, plain, 5.0, width=1280, height=720, fps=24, crf=20)

st = gr.analyze(plain)
target = gr.median_stats([st, st])
graded = TMP / "graded.mp4"
gr.grade_shot(plain, graded, target, strength=0.9, measured=st, crf=20, preset="medium", fps=24)


def streams(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return r.stdout.strip().replace("\n", " | ")


print("原片   :", streams(src))
print("普通片段:", streams(plain))
print("调色片段:", streams(graded))

out = TMP / "concat.mp4"
ff.concat_videos([str(plain), str(graded)], out)
print("concat :", streams(out))
