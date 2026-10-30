"""How long does one segment take on the 3090?

The music clips took eighteen minutes each, which would put a thirty-three
segment episode at ten hours.  The number has to be measured, not guessed.
"""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.visual import regen_shot
from dramakit.project import ProjectStore

# a copy of the project with the previous episode in it - the shot and its
# prompt are good enough to time the machine
work = Path(r"C:\\tmp\\timing_proj")
if work.exists():
    shutil.rmtree(work, ignore_errors=True)
shutil.copytree(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\proj_backup_ep1", work)

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(work)
proj = store.load()
ep = proj.episodes[0]
shot = ep.scenes[0].shots[0]
print("镜头:", shot.id, "原时长", shot.duration)

t0 = time.time()
res = regen_shot(store, cfg, 1, shot.id, mode="video")
dt = time.time() - t0
print(f"结果: {res.get('ok')}  用时 {dt/60:.1f} 分钟  时长 {res.get('duration')}")
p = work / "video" / f"shot_{shot.id}.mp4"
if p.exists():
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,duration,width,height",
                          "-of", "default=noprint_wrappers=1", str(p)],
                         capture_output=True, text=True)
    print(out.stdout)
    print(f"每帧耗时: {dt/max(1e-6,float(res.get('duration') or 1)):.2f}s/秒画面")
