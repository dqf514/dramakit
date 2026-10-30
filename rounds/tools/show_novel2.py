"""The screenplay and the director's plan, on their own."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
p = ProjectStore(Path(r"E:\\dramakit\\projects") / name).load()
out = []
for ep in p.episodes:
    out.append(f"=== 第{ep.index}集 {ep.title}")
    for sc in ep.scenes:
        out.append(f"  场{sc.index} @ {sc.location} {sc.time_of_day} | {sc.summary}")
        for l in sc.lines:
            out.append(f"      [{l.kind.value}] {l.speaker}: 「{l.text}」 ({l.emotion})")
    out.append("")
    out.append("  --- 导演的分镜（片段）---")
    for sc in ep.scenes:
        for sh in sc.shots:
            out.append(f"   镜{sh.index} {sh.shot_type.value}/{sh.camera_move} "
                       f"{sh.duration:.1f}s 台词{sh.line_indices}")
            out.append(f"       {(sh.action or '')[:160]}")
Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\novel_out.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("写到 novel_out.txt，", len(out), "行")
