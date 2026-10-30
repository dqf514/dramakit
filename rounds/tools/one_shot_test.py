"""One shot, end to end, before the whole episode is spent.

The reference pictures go into their slots, the voice recording goes in as
the audio reference, and the clip has to come back with a voice in it.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.visual import regen_shot
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
shot_id = sys.argv[2] if len(sys.argv) > 2 else "sh-897b2efc"

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
res = regen_shot(store, cfg, 1, shot_id, mode="video")
print("结果:", res)

p = store.root / "video" / f"shot_{shot_id}.mp4"
print("文件:", p, p.exists() and p.stat().st_size or "没有")
if p.exists():
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,duration",
                          "-of", "default=noprint_wrappers=1", str(p)],
                         capture_output=True, text=True)
    print(out.stdout)
    # the voice has to be in there
    wav = Path(r"C:\\tmp\\test_voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vn",
                    "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)
    print("转写…")
    r = subprocess.run([r"E:\\ComfyUI\\venv\\Scripts\\python.exe",
                        r"E:\\dramakit\\rounds\\tools\\transcribe3.py", str(wav)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (r.stdout or "").splitlines():
        if "原样" in line or "人声频段" in line:
            print("  ", line.strip())
