"""Does every scene in the project find its room asset?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.refs import find_location, missing_references, picture_plan
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母"))
ctx = Context(cfg, store)

print("场景 -> 房间资产")
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        loc = find_location(ctx, sc.location)
        refs = len(loc.ref_images) if loc else 0
        print(f"  第{ep.index}集 场{sc.index}: {sc.location!r:<28} -> "
              f"{(loc.name if loc else '(没找到)')!r:<24} 参考图{refs} 张")

print()
print("第1集每一镜的参考图清单:")
ep = ctx.project.episodes[0]
for sc in ep.scenes:
    for sh in sc.shots:
        miss = missing_references(ctx, sh, sc)
        plan = picture_plan(ctx, sh, sc)
        if sh.index <= 3 or miss:
            print(f"  {sh.id} {sh.shot_type.value:<4} 人物{sh.characters} "
                  f"→ {len(plan)} 张参考图 {[k for _p,_w,k in plan]}"
                  + (f"  缺: {miss}" if miss else ""))
