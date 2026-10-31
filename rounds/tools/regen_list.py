"""Draw these segments again, one after the other."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.visual import regen_shot
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 1
ids = sys.argv[3].split(",")

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
for sid in ids:
    t0 = time.time()
    res = regen_shot(store, cfg, ep_index, sid.strip(), mode="video")
    print(f"{sid}: ok={res.get('ok')} 用时 {(time.time()-t0)/60:.1f} 分钟 "
          f"{res.get('error') or ''}", flush=True)
