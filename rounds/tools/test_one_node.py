"""Send one H3 job to one specific node."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
which = sys.argv[2] if len(sys.argv) > 2 else "gpu3090-b"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects") / name))
pool = ctx.providers.visual
node = next(n for n in pool.nodes if n.name == which)
print(f"节点 {node.name} -> {node.client.base}")

ep = ctx.target_episodes()[0]
shot = next(sh for sc in ep.scenes for sh in sc.shots)
img = ctx.store.abs(shot.image_path)
out = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode") / f"{which}.mp4"
t0 = time.time()
node.client.generate_video(shot.video_prompt or shot.prompt, "",
                           image_path=str(img), frames=56, fps=24,
                           seed=20260401, out_path=str(out))
print(f"用时 {time.time()-t0:.0f}s -> {out.stat().st_size} 字节")
print("--- 显卡占用 ---")
import subprocess
print(subprocess.run(["ssh", "-o", "BatchMode=yes", "-i",
                      r"C:\\Users\\David\\.ssh\\id_ed25519",
                      "david@192.168.31.7",
                      "nvidia-smi --query-gpu=index,memory.used --format=csv,noheader"],
                     capture_output=True, text=True).stdout)
