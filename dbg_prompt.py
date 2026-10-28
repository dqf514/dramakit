import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
p = ProjectStore(Path(r"E:\\dramakit\\projects") / name).load()
sc = p.episodes[0].scenes[0]
want = sys.argv[2:] if len(sys.argv) > 2 else None
for sh in sc.shots:
    if want and sh.id not in want and str(sh.index) not in want:
        continue
    vp = sh.video_prompt or ""
    i = vp.find("integrated_multimodal_description")
    j = vp.find("overall_soundscape")
    print("=" * 70)
    print(f"{sh.id}  {sh.shot_type.value}  lines={sh.line_indices}  "
          f"人物={sh.characters}")
    print(vp[i:j if j > 0 else i + 2200].strip())
    print()
