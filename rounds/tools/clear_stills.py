"""Clear the stills so they are made again with the real prompts.

The promptgen stage was interrupted, so the shots have no picture prompt
and the stills were made from the fallback text. The prompts are there
now; the pictures have to be made again.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
proj = store.load()
n = 0
for ep in proj.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if sh.image_path:
                p = store.abs(sh.image_path)
                if p.exists():
                    p.unlink()
                sh.image_path = ""
                n += 1
store.save(proj)
print(f"{name}: 清掉 {n} 张要重出的首帧")
