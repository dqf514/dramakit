import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.models import is_narration
from dramakit.project import ProjectStore

name = sys.argv[1]
p = ProjectStore(Path(r"E:\\dramakit\\projects") / name).load()
for sc in p.episodes[0].scenes:
    print(f"=== 场景 {sc.index}")
    spoken = [l for l in sc.lines if not is_narration(l)]
    for sh in sc.shots:
        who = "、".join(sh.characters or []) or "（无人）"
        print(f"  镜{sh.index} {sh.shot_type.value:<4} 人物={who}")
        print(f"      动作：{(sh.action or '')[:96]}")
        for n in sh.line_indices:
            if 1 <= n <= len(spoken):
                l = spoken[n - 1]
                mark = "  <-- 说话人不在画面里" if l.speaker not in (sh.characters or []) else ""
                print(f"      台词{n} {l.speaker}：「{l.text[:18]}」{mark}")
