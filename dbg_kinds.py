import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1]
p = ProjectStore(Path(r"E:\dramakit\projects") / name).load()
for sc in p.episodes[0].scenes:
    print(f"=== 场景 {sc.index}")
    for l in sc.lines:
        audio = "有" if l.audio_path else "无"
        print(f"  {l.kind.value:<9} dur={l.duration:7.3f} 音频={audio} "
              f"{l.speaker:<8} 「{l.text[:22]}」")
