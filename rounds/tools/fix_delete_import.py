"""The handler needs shutil and time where it moves a project."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

if "\nimport shutil\nimport time" not in s:
    # put them where the module's own imports are
    anchor = "\nfrom pathlib import Path\n"
    i = s.find(anchor)
    assert i > 0, "没找到 import 区"
    s = s[:i] + anchor + "import shutil\nimport time\n" + s[i + len(anchor):]
    p.write_text(s, encoding="utf-8")
    print("web/server.py: import shutil / time")
else:
    print("web/server.py: 已经有了")
