"""Look at the director's plan for one episode."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
p = ProjectStore(Path(r"E:\\dramakit\\projects") / name).load()
ep = p.episodes[int(sys.argv[2]) - 1] if len(sys.argv) > 2 else p.episodes[0]
out = [f"=== 第{ep.index}集 {ep.title}"]
for sc in ep.scenes:
    out.append(f"  场{sc.index} @ {sc.location} {sc.time_of_day} | {sc.summary}")
    for l in sc.lines:
        out.append(f"      {l.speaker}: 「{l.text}」 ({l.emotion})")
out.append("")
out.append("--- 片段（导演的方案）---")
for sc in ep.scenes:
    for sh in sc.shots:
        out.append(f"  镜{sh.index} {sh.shot_type.value}/{sh.camera_move} "
                   f"{sh.duration:.1f}s 台词{sh.line_indices} 人物{sh.characters}")
        out.append(f"      {(sh.action or '')[:220]}")
Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\plan.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("写到 plan.txt，", len(out), "行")
