"""The concat demuxer vs the filter concat on the same mp3 parts."""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

proj = Path(r"E:\dramakit\projects") / "轮次02_02"
audio = sorted((proj / "audio").glob("*.mp3"))
parts = audio[:11]          # scene 0 of round 2
out = Path(r"C:\Users\David\AppData\Local\Temp\opencode")

total = sum(ff.probe_duration(p) for p in parts)
print(f"11 个音频文件的真实总长: {total:.2f}s")

# 1) the concat demuxer (what concat_audio does today)
lst = out / "parts.txt"
with open(lst, "w", encoding="utf-8") as f:
    for p in parts:
        f.write(f"file '{p.resolve().as_posix()}'\n")
dem = out / "demuxer.mp3"
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c:a", "libmp3lame", "-q:a", "4", str(dem)],
               capture_output=True)
print(f"concat 解复用器:        {ff.probe_duration(dem):.2f}s")

# 2) the filter concat (the fallback in concat_audio)
filt = out / "filter.mp3"
cmd = ["ffmpeg", "-y"]
for p in parts:
    cmd += ["-i", str(p)]
n = len(parts)
filtstr = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
cmd += ["-filter_complex", filtstr, "-map", "[a]", "-c:a", "libmp3lame", "-q:a", "4",
        str(filt)]
subprocess.run(cmd, capture_output=True)
print(f"filter concat:          {ff.probe_duration(filt):.2f}s")

# 3) what the mp3 headers claim
r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=bit_rate,codec_name,duration",
                    "-of", "default=nw=1", str(parts[0])], capture_output=True, text=True)
print("第一个文件的流信息:", r.stdout.replace("\n", " "))
