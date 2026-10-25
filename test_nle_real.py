"""Dry-run the FCPXML export with the real project's timeline."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context, build_timeline
from dramakit.pipeline import compose as C
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\测试短剧")
store = ProjectStore(root)
ctx = Context(cfg, store)

ep = ctx.target_episodes()[0]
tl = build_timeline(ep)
print(f"第{ep.index}集 时间线 {tl.duration:.1f}s / {len(tl.shots)} 镜 / {len(tl.lines)} 句")

# 用真实的首帧文件当作 clip（compose 里也是这样复制的）
shot_clips = []
for i, ts in enumerate(tl.shots):
    p = ctx.store.abs(ts.shot.image_path) if ts.shot.image_path else None
    if p and p.exists():
        shot_clips.append((str(p), ts))
print("可用的镜头首帧:", len(shot_clips))

out = C._export_nle(ctx, ep, tl, shot_clips, None)
print("导出:", out)

import xml.etree.ElementTree as ET
rootel = ET.parse(out).getroot()
spine = rootel.findall(".//spine/asset-clip")
sections = rootel.findall(".//section")
print(f"  spine 片段 {len(spine)}，音轨 {len(sections)}")
for s in sections:
    print(f"    lane {s.get('lane')} '{s.get('name')}' clips={len(s.findall('asset-clip'))}")
assets = rootel.findall(".//resources/asset")
print(f"  资源 {len(assets)} 个")
print(f"  文件大小 {Path(out).stat().st_size/1024:.0f} KB")
