"""How fast is the 3090 at one segment?

Submitted straight to ComfyUI with the same workflow, the same five
reference slots and the same number of frames a ten second segment needs.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.providers import Providers
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母"))
pool = Providers(cfg, store.root)
vis = pool.visual
print("视频节点:", [n.name for n in getattr(vis, "nodes", [])])

proj = store.load()
refs = []
for c in proj.characters[:1]:
    for rel in c.refs()[:1]:
        p = store.abs(rel)
        if p.exists():
            refs.append(str(p))
for loc in proj.locations[:1]:
    for rel in (loc.ref_images or [])[:1]:
        p = store.abs(rel)
        if p.exists():
            refs.append(str(p))
print("参考图:", len(refs), [Path(r).name for r in refs])

frames = int(sys.argv[1]) if len(sys.argv) > 1 else 243
out = Path(r"C:\\tmp\\timing.mp4")
t0 = time.time()
vis.generate_video(
    prompt=("subject_definitions:\n<Picture 1> is the views of 苏晚.\n"
            "detailed_description:\n[Shot 1] A woman in a wedding gown stands on "
            "a stage and speaks. <d>[zh-CN]这婚换个人结！</d>\n"
            "overall_soundscape: A banquet hall.\nnon_diegetic_music: N/A"),
    negative="",
    image_path="",
    frames=frames, fps=24, seed=12345, out_path=str(out),
    extra={"ref_pictures": refs})
dt = time.time() - t0
print(f"\n{frames} 帧（{frames/24:.1f} 秒画面）用时 {dt/60:.1f} 分钟 "
      f"= {dt/frames:.2f} 秒/帧")
r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                    "stream=codec_type,duration,width,height",
                    "-of", "default=noprint_wrappers=1", str(out)],
                   capture_output=True, text=True)
print(r.stdout)
