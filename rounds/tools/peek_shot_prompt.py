"""What the prompt for a failed shot actually says."""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.project import ProjectStore  # noqa: E402

slug = "穿成亿万总裁他前妻"
store = ProjectStore.open(ROOT / "projects" / slug)
proj = store.load()

shown = 0
for ep in proj.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            need = len([n for n in (sh.line_indices or []) if n > 0])
            have = (sh.video_prompt or "").count("<d>")
            if need and have < need:
                print("=" * 70)
                print("  集%s 场%s 镜%s  需要台词 %d 句，提示词里 <d> %d 个"
                      % (ep.index, sc.index, sh.id[:10], need, have))
                print("  status:", sh.status)
                print("  --- video_prompt ---")
                print((sh.video_prompt or "")[:900])
                print("  --- image_prompt ---")
                print((sh.prompt or "")[:300])
                shown += 1
                if shown >= 2:
                    raise SystemExit(0)
print("  没有失败的镜")
