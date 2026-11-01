"""What the web console can do."""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
t = Path(r"E:\\dramakit\\dramakit\\web\\server.py").read_text(encoding="utf-8")
print("=== 路由 ===")
for m in re.finditer(r'@(app|router)\.(get|post|put|delete)\("([^"]+)"', t):
    print(f"  {m.group(2).upper():5} {m.group(3)}")
print()
print("=== 新建项目/上传源文件相关 ===")
for pat in ("source_file", "upload", "new_project", "novel", "source"):
    hits = [i + 1 for i, l in enumerate(t.splitlines()) if pat in l.lower()]
    print(f"  {pat}: {len(hits)} 处" + (f"（行 {hits[:6]}）" if hits else ""))
