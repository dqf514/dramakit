"""How far along is the render?"""
import subprocess
import sys
import time
from pathlib import Path

root = Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
vids = sorted((root / "video").glob("*.mp4"), key=lambda p: p.stat().st_mtime)
imgs = list((root / "images").glob("shot_*.png"))
print(f"现在 {time.strftime('%H:%M')} | 首帧 {len(imgs)} | 视频 {len(vids)}/33")
for p in vids[-3:]:
    print(f"   {time.strftime('%H:%M', time.localtime(p.stat().st_mtime))}  {p.name}")
if vids:
    first = vids[0].stat().st_mtime
    last = vids[-1].stat().st_mtime
    span = last - first
    per = span / max(1, len(vids) - 1) / 60
    left = (33 - len(vids)) * per
    print(f"   每段 {per:.1f} 分钟；还剩 {left/60:.1f} 小时，"
          f"预计 {time.strftime('%H:%M', time.localtime(time.time()+left*60))} 完成")
