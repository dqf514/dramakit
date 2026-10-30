"""Repair the project file: a scene status that was written as null."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
f = root / "project.json"
d = json.loads(f.read_text(encoding="utf-8"))

ok = {"pending", "running", "done", "failed", "skipped"}
fixed = 0


def walk(node):
    global fixed
    if isinstance(node, dict):
        st = node.get("status")
        if st is None and "id" in node:
            node["status"] = "pending"
            fixed += 1
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)


walk(d)
f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"修了 {fixed} 个空的 status")
