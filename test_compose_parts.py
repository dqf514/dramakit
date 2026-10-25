"""Exercise the new compose pieces without touching the GPU."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff
from dramakit.media import nle

TMP = Path(r"C:\Users\David\AppData\Local\Temp\opencode\composetest")
TMP.mkdir(parents=True, exist_ok=True)

# --- 1) two-pass loudness normalisation ---
src = TMP / "src.mp3"
ff._run([ff.ffmpeg_bin(), "-y", "-f", "lavfi", "-i",
         "sine=frequency=440:duration=6,volume=0.05", str(src)], quiet=True)
norm = TMP / "norm.mp3"
t0 = time.time()
ff.normalize_loudness(src, norm, target_lufs=-24.0, tp=-2.0)
print(f"归一 {time.time()-t0:.1f}s -> {norm.stat().st_size/1024:.0f} KB")

r = ff._run([ff.ffmpeg_bin(), "-i", str(norm), "-af", "ebur128=peak=true",
             "-f", "null", "-"], quiet=True)
text = r.stderr
i = text.rfind("Summary:")
seg = text[i:] if i >= 0 else text
import re
print("  归一后响度:", re.search(r"I:\s*(-?[\d.]+)\s*LUFS", seg).group(1), "LUFS")

# --- 2) music stem: bed + bgm with their own gains ---
bed = TMP / "bed.mp3"
bgm = TMP / "bgm.mp3"
ff._run([ff.ffmpeg_bin(), "-y", "-f", "lavfi", "-i",
         "sine=frequency=220:duration=6,volume=0.3", str(bed)], quiet=True)
ff._run([ff.ffmpeg_bin(), "-y", "-f", "lavfi", "-i",
         "sine=frequency=330:duration=6,volume=0.3", str(bgm)], quiet=True)
stem = TMP / "music.mp3"
ff.mix_tracks([(str(bed), 0.45), (str(bgm), 0.22)], stem, duration=6.0)
print("music stem:", stem.stat().st_size / 1024, "KB")

# --- 3) final mix with ducking ---
voice = TMP / "voice.mp3"
ff._run([ff.ffmpeg_bin(), "-y", "-f", "lavfi", "-i",
         "sine=frequency=660:duration=6,volume=0.5", str(voice)], quiet=True)
mix = TMP / "mix.mp3"
ff.mix_voice_bgm(voice, str(stem), mix, bgm_volume=1.0, duck=True,
                 target_lufs=-16.0)
print("mix:", mix.stat().st_size / 1024, "KB")
r = ff._run([ff.ffmpeg_bin(), "-i", str(mix), "-af", "ebur128=peak=true",
             "-f", "null", "-"], quiet=True)
seg = r.stderr[r.stderr.rfind("Summary:"):]
print("  成片响度:", re.search(r"I:\s*(-?[\d.]+)\s*LUFS", seg).group(1), "LUFS",
      " 峰值:", re.search(r"Peak:\s*(-?[\d.]+)\s*dBFS", seg).group(1), "dBFS")

# --- 4) FCPXML export with dialogue + music lanes ---
tl = nle.Timeline(name="EP001", width=1280, height=720, fps=24, duration=12.0)
tl.video = [nle.Clip(src=TMP / "a.mp4", offset=i * 4.0, duration=4.0,
                     name=f"shot_{i}", has_video=True, has_audio=False)
            for i in range(3)]
tl.lanes[1] = ("Dialogue", [nle.Clip(src=voice, offset=1.0, duration=3.2,
                                     name="林凡_1", has_video=False, has_audio=True)])
tl.lanes[2] = ("Music", [nle.Clip(src=stem, offset=0.0, duration=12.0,
                                  name="music", has_video=False, has_audio=True)])
out = nle.write_fcpxml(tl, TMP / "ep.fcpxml")
import xml.etree.ElementTree as ET
root = ET.parse(out).getroot()
print("FCPXML:", root.tag, root.get("version"),
      "spine=", len(root.findall(".//spine/asset-clip")),
      "lanes=", len(root.findall(".//section")))
