"""A name imported inside one method is not imported for the module.

settle_leftover_runs compares against Status.RUNNING and raised NameError
on every boot, because the only import of Status in the file lived inside
_api_character_update - a local one, invisible to the rest of the module.
The guard meant to add the real import looked for the string anywhere in
the file, found the local one, and concluded there was nothing to do.

So the import goes at the top, where every method can see it, and the
local one - now redundant - goes away, so the next reader is not sent
looking for a difference that does not matter.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
lines = p.read_text(encoding="utf-8").split("\n")

# remove the local import inside _api_character_update
local = "            from ..models import Status"
idx = [n for n, l in enumerate(lines) if l == local]
assert idx, "没找到局部的 Status 导入"
for n in idx:
    del lines[n]
    print(f"  删掉局部导入（原第 {n + 1} 行）")

# add the module-level one, right after Config
anchor = [n for n, l in enumerate(lines)
          if l == "from ..config import Config"]
assert anchor, "没找到 Config 导入"
n = anchor[0]
if lines[n + 1].strip() != "from ..models import Status":
    lines.insert(n + 1, "from ..models import Status")
    print(f"  模块级导入加在第 {n + 2} 行")

p.write_text("\n".join(lines), encoding="utf-8")
print("server.py: Status 现在是模块级导入")
