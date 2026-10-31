"""The visual stage takes the path of a file; it never imported Path."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")
old = "import hashlib\nimport time\n"
new = "import hashlib\nimport time\nfrom pathlib import Path\n"
assert old in s, "import 锚点没找到"
assert "from pathlib import Path" not in s.split("def ")[0], "已经有了"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("visual.py: import Path")
