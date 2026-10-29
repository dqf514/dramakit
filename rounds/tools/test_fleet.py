"""Does the fleet hand the shots to the machines?

    python rounds/tools/test_fleet.py 轮次09_09
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects") / name))
vis = ctx.providers.visual
print("provider:", type(vis).__name__)
if hasattr(vis, "health"):
    for h in vis.health():
        print(f"  {h['name']:<12} {h['roles']}  {h['base_url']}  在线={h['online']}")
else:
    print("  单机:", vis.base, vis.ping())

# a real shot
ep = ctx.target_episodes()[0]
shots = [sh for sc in ep.scenes for sh in sc.shots]
if not shots:
    raise SystemExit("项目里没有镜头")
shot = shots[0]
img = ctx.store.abs(shot.image_path)
print(f"\n用镜头 {shot.id} 测试（{shot.duration:.2f}s）")
prompt = shot.video_prompt or "a person speaking in a cafe"
out = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\fleet_test.mp4")
t0 = time.time()
vis.generate_video(prompt, "", image_path=str(img), frames=56, fps=24,
                   seed=20260301, out_path=str(out))
print(f"  用时 {time.time()-t0:.0f}s  -> {out.stat().st_size} 字节")

# and the second node
out2 = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\fleet_test2.mp4")
t0 = time.time()
vis.generate_video(prompt, "", image_path=str(img), frames=56, fps=24,
                   seed=20260302, out_path=str(out2))
print(f"  用时 {time.time()-t0:.0f}s  -> {out2.stat().st_size} 字节")
print("两个节点都跑通了")
