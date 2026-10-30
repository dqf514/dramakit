"""Show what the screenwriter and the director made of the novel."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
p = ProjectStore(Path(r"E:\\dramakit\\projects") / name).load()
meta = p.meta
print("剧名:", getattr(meta, "title", ""), "| 题材:", getattr(meta, "genre", ""))
print("一句话故事:", getattr(meta, "synopsis", ""))
print()
print("人物（编剧读出来的）：")
for c in p.characters:
    print(f"  {c.name:<6} {c.role:<8} {c.gender}/{c.age}  {c.personality[:26]}")
    print(f"         外貌: {c.appearance[:60]}")
print()
print("场景（美术设定）：")
for l in p.locations:
    print(f"  {l.name}: {(l.visual_prompt or '')[:110]}")
print()
print("道具（资产库第三层）：")
for x in getattr(p, "props", []) or []:
    print(f"  {x.name}: {(x.visual_prompt or '')[:100]}")
print()
print("美术:", p.art_direction.style, "|", p.art_direction.era, "|",
      p.art_direction.color_palette)
print()
for ep in p.episodes:
    print(f"=== 第{ep.index}集 {ep.title}")
    for sc in ep.scenes:
        print(f"  场{sc.index} @ {sc.location} {sc.time_of_day} | {sc.summary}")
        for l in sc.lines:
            print(f"      [{l.kind.value}] {l.speaker}: 「{l.text}」 ({l.emotion})")
    print()
    print("  --- 导演的分镜（片段）---")
    for sc in ep.scenes:
        for sh in sc.shots:
            print(f"   镜{sh.index} {sh.shot_type.value}/{sh.camera_move} "
                  f"{sh.duration:.1f}s 台词{sh.line_indices}")
            print(f"       {(sh.action or '')[:150]}")
