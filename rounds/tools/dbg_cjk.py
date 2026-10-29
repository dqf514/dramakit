"""What Chinese is left in the prompt H3 gets?"""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
p = ProjectStore(Path(r"E:\\dramakit\\projects") / name).load()
sc = p.episodes[0].scenes[0]
for sh in sc.shots[:4]:
    vp = sh.video_prompt or ""
    # chinese runs, with the punctuation that goes with them
    cjk = re.findall(r"[\u4e00-\u9fff][\u4e00-\u9fff\s，。：、！？…]{1,30}", vp)
    print("===", sh.id, sh.shot_type.value)
    for c in cjk[:8]:
        print("    ", c.strip())
    if not cjk:
        print("     （没有中文）")
