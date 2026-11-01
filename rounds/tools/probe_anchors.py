"""The exact bytes of the pieces the chapters patch has to find."""
from pathlib import Path

t = Path(r"E:\dramakit\dramakit\ai\actions.py").read_text(encoding="utf-8")

out = []
i = t.index('"run_pipeline": {')
out.append("=== run_pipeline 定义 ===")
out.append(repr(t[i:i + 240]))

j = t.index('if "episodes" in allowed:')
out.append("")
out.append("=== episodes 归一化 ===")
out.append(repr(t[j - 110:j + 130]))

k = t.index('if p.get("episodes"):')
out.append("")
out.append("=== _do_run 里的 episodes ===")
out.append(repr(t[k - 60:k + 170]))

m = t.find("eps = f\"")
out.append("")
out.append("=== 摘要文案 ===")
out.append(repr(t[m - 40:m + 200]) if m > 0 else "(未找到)")

n = t.find('"输出格式:')
out.append("")
out.append("=== 解析提示词 ===")
out.append(repr(t[n:n + 400]) if n > 0 else "(未找到)")

r = t.find('"规则:')
out.append("")
out.append(repr(t[r:r + 300]) if r > 0 else "(未找到 规则)")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\anchors.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
