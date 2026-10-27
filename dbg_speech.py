"""How much speech is in the H3 audio?

Compares the native audio of clips whose prompt asked for a speaking
character with clips whose prompt did not. Speech shows up as a strong
envelope modulation at the syllable rate, which is what this measures.
"""
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")


def pcm(path):
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "8000",
         "-f", "s16le", "-"], capture_output=True)
    data = r.stdout
    n = len(data) // 2
    a = list(struct.unpack(f"<{n}h", data[:n * 2]))
    return a


def envelope_modulation(samples, rate=8000):
    """The strength of the 2-8 Hz envelope modulation (speech territory)."""
    if len(samples) < rate:
        return 0.0, 0.0
    win = rate // 20                      # 50 ms
    env = []
    for i in range(0, len(samples) - win, win):
        seg = samples[i:i + win]
        env.append(sum(abs(v) for v in seg) / win)
    if len(env) < 10:
        return 0.0, 0.0
    mean = sum(env) / len(env)
    if mean <= 0:
        return 0.0, 0.0
    # the difference between the fast and the slow movement of the envelope
    fast = [env[i + 1] - env[i] for i in range(len(env) - 1)]
    slow = [env[i + 5] - env[i] for i in range(len(env) - 5)]
    mf = sum(abs(v) for v in fast) / len(fast)
    ms = sum(abs(v) for v in slow) / len(slow)
    return mf / mean, ms / mean


def loudness(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-af",
                        "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    import re
    m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", r.stderr)
    return float(m.group(1)) if m else 0.0


for name in sys.argv[1:]:
    proj = Path(r"E:\dramakit\projects") / name
    tmp = proj / "video"
    print(f"=== {name} ===")
    for clip in sorted(tmp.glob("shot_*.mp4"))[:6]:
        a = pcm(clip)
        if not a:
            continue
        mf, ms = envelope_modulation(a)
        print(f"  {clip.name}: 响度 {loudness(clip):6.1f} LUFS  "
              f"包络快变 {mf:.3f}  慢变 {ms:.3f}  比 {mf/max(ms,1e-6):.2f}")
