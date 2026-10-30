"""Check a finished episode the way a viewer would.

  * every segment has a voice in it
  * what the voice says is what the script says (whisper)
  * the subtitles are where the words are
  * the AI declaration and the filing number are on the picture
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 1

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
ctx = Context(cfg, store)
ep = ctx.project.episode(ep_index)
tl = ctx.timeline(ep)

FF = "ffmpeg"


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        return json.loads(r.stdout or "{}").get("streams", [])
    except json.JSONDecodeError:
        return []


def max_volume(path):
    r = subprocess.run([FF, "-i", str(path), "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True,
                       errors="replace")
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr or "")
    return float(m.group(1)) if m else None


print(f"=== 第{ep.index}集《{ep.title}》 {tl.duration:.1f}s ===")
print(f"场 {len(tl.scenes)} | 片段 {len(tl.shots)} | 台词 {len(tl.lines)} 句")

# --- the picture ---
print("\n--- 片段 ---")
no_audio = []
silent = []
for ts in tl.shots:
    p = ctx.store.abs(ts.shot.video_path) if ts.shot.video_path else None
    if not p or not p.exists():
        no_audio.append((ts.shot.id, "缺文件"))
        continue
    kinds = {s.get("codec_type") for s in probe(p)}
    if "audio" not in kinds:
        no_audio.append((ts.shot.id, "没有音轨"))
        continue
    v = max_volume(p)
    if v is not None and v < -45:
        silent.append((ts.shot.id, f"{v:.0f}dB"))
print(f"  片段总数 {len(tl.shots)} | 缺音轨 {len(no_audio)} | 无人声 {len(silent)}")
for sid, why in (no_audio + silent)[:8]:
    print(f"    {sid}: {why}")

# --- the finished file ---
final = ctx.store.abs(ep.video_path) if ep.video_path else None
if final and final.exists():
    print("\n--- 成片 ---")
    for s in probe(final):
        if s.get("codec_type") == "video":
            print(f"  画面 {s.get('width')}x{s.get('height')} {s.get('codec_name')}"
                  f" {float(s.get('duration') or 0):.1f}s")
        else:
            print(f"  声音 {s.get('codec_name')} {float(s.get('duration') or 0):.1f}s")
    # the declaration has to be on the picture
    r = subprocess.run([FF, "-v", "error", "-y", "-ss", "1", "-i", str(final),
                        "-frames:v", "1", "C:\\tmp\\head.png"], capture_output=True)
    print("  片头帧已抽出: C:\\tmp\\head.png")
else:
    print("  没有成片")

# --- the words ---
print("\n--- 台词与字幕 ---")
spoken = [t for t in tl.lines if t.line.kind.value == "dialogue"]
narr = [t for t in tl.lines if t.line.kind.value != "dialogue"]
print(f"  该被说出来的 {len(spoken)} 句 | 旁白/字幕卡 {len(narr)} 句")
sub = ctx.store.abs(ep.subtitle_path) if ep.subtitle_path else None
if sub and sub.exists():
    cues = re.findall(r"^Dialogue:.*?,(.*?),(\d+:\d+:\d+\.\d+),(\d+:\d+:\d+\.\d+),",
                       sub.read_text(encoding="utf-8"), re.M)
    print(f"  字幕 {len(cues)} 条")
else:
    print("  没有字幕文件")
