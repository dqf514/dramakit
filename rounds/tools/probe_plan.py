"""What did the production plan ask for, and what does it actually do?

The user asked for the first ten episodes as video; the segment stage is
cutting every chapter of the book into an episode. Two questions: did the
request carry the episode limit, and would segment have respected it
anyway. This reads the action's declared parameters and every place the
limit is honoured.
"""
import re
from pathlib import Path

out = []

a = Path(r"E:\dramakit\dramakit\ai\actions.py").read_text(encoding="utf-8")
i = a.find('"run_pipeline"')
out.append("=== actions.py 里 run_pipeline 的参数声明 ===")
out.append(a[max(0, i - 120):i + 700])

out.append("")
out.append("=== _build 怎么处理 episodes ===")
j = a.find("def _build")
if j > 0:
    out.append(a[j:j + 900])

out.append("")
out.append("=== _do_run 里 episodes 的用法 ===")
k = a.find("def _do_run")
if k > 0:
    seg = a[k:k + 1200]
    for line in seg.split("\n"):
        if "episode" in line or "only_" in line or "stages" in line:
            out.append("  " + line.strip()[:120])

out.append("")
out.append("=== target_episodes 的过滤 ===")
b = Path(r"E:\dramakit\dramakit\pipeline\base.py").read_text(encoding="utf-8")
m = b.find("def target_episodes")
out.append(b[m:m + 600] if m > 0 else "(未找到)")

out.append("")
out.append("=== segment 里有没有用 only_episodes / target_episodes ===")
s = Path(r"E:\dramakit\dramakit\pipeline\segment.py").read_text(encoding="utf-8")
hits = [f"  行{n}: {l.strip()[:110]}"
        for n, l in enumerate(s.split("\n"), 1)
        if "only_episodes" in l or "target_episodes" in l]
out.append("\n".join(hits) if hits else "  没有 —— segment 不看集数限制")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\plan.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
