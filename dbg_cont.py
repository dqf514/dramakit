"""Do the shot prompts carry the previous shot's state?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

proj = Path(r"E:\dramakit\projects") / sys.argv[1]
p = ProjectStore(proj).load()
for ep in p.episodes:
    for sc in ep.scenes:
        prev = ""
        for sh in sc.shots:
            pr = (sh.prompt or "")
            # a few words from the previous shot's action showing up in this
            # shot's prompt means the continuity reached the model
            hit = ""
            if prev:
                for frag in prev.replace("，", " ").replace("。", " ").split():
                    if len(frag) >= 3 and frag in pr:
                        hit = frag
                        break
            print(f"  {sh.id} 上一镜动作命中提示词: {hit or '（无）'}")
            print(f"      {pr[:150]}")
            prev = sh.action or ""
