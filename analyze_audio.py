"""Analyse the sound: voice track, music bed, mix balance, and the casting."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff
from dramakit.config import Config
from dramakit.project import ProjectStore

root = Path(r"E:\dramakit\projects\测试短剧")
cfg = Config.load(r"E:\dramakit\config\default.yaml")
store = ProjectStore(root)
proj = store.load()
ep = proj.episodes[0]


def loud(path, label):
    r = ff._run([ff.ffmpeg_bin(), "-i", str(path), "-af", "ebur128=peak=true",
                 "-f", "null", "-"], quiet=True)
    seg = r.stderr[r.stderr.rfind("Summary:"):]
    out = {}
    for key, pat in (("I", r"I:\s*(-?[\d.]+)\s*LUFS"), ("LRA", r"LRA:\s*(-?[\d.]+)\s*LU"),
                     ("PK", r"Peak:\s*(-?[\d.]+)\s*dBFS")):
        m = re.search(pat, seg)
        if m:
            out[key] = float(m.group(1))
    print(f"  {label:28s} {out.get('I')} LUFS  LRA {out.get('LRA')}  峰值 {out.get('PK')} dBFS")
    return out


print("=== 角色选角 ===")
for c in proj.characters:
    print(f"  {c.name:6s} {c.role or '':6s} 音色={c.voice_id:24s} "
          f"音高={c.voice_pitch} 语速={c.voice_rate}")

print("\n=== 逐句配音文件 ===")
for sc in ep.scenes:
    for l in sc.lines:
        if not l.audio_path:
            print(f"  [{l.kind.value:9s}] {l.speaker or '-':6s} {l.duration:5.2f}s  (无音频) {l.text[:28]}")
            continue
        p = store.abs(l.audio_path)
        d = ff.probe_duration(p)
        sz = p.stat().st_size / 1024
        print(f"  [{l.kind.value:9s}] {l.speaker or '-':6s} 标注{l.duration:5.2f}s 实际{d:5.2f}s "
              f"{sz:6.0f}KB  {l.text[:26]}")

print("\n=== 集1 音频层次 ===")
loud(root / "episodes" / "ep_001.mp4", "成片")

# 单独把对白轨和音乐轨拉出来比较
proj_dir = root
mix = proj_dir / "tmp"
print("\n=== 抽测：对白 vs 垫底的相对关系 ===")
for f in sorted((root / "episodes").glob("*.mp4")):
    # 用 volumedetect 看整体，再看是否有段落低于阈值（听不清）
    r = ff._run([ff.ffmpeg_bin(), "-i", str(f), "-af",
                 "astats=metadata=1:reset=0", "-f", "null", "-"], quiet=True)
    rms = [float(x) for x in re.findall(r"RMS level dB: (-?[\d.]+)", r.stderr)]
    rms = [x for x in rms if x > -120]
    if rms:
        rms_sorted = sorted(rms)
        p10 = rms_sorted[len(rms) // 10]
        p50 = rms_sorted[len(rms) // 2]
        print(f"  {f.name}: RMS 中位 {p50:.1f} dB  10分位 {p10:.1f} dB  "
              f"最低 {min(rms):.1f} dB")
