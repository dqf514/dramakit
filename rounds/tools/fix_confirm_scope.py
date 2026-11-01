"""Say the chapters in the plan, not just the episodes.

The confirm dialog built a line about episodes and my patch added a
variable about chapters beside it without using it - so a plan that read
"前十章" as ten episodes showed the user nothing wrong before it ran.
The message names both: the chapters the book will be cut from, and the
episodes that will be worked on, which are different things.
"""
import re
from pathlib import Path

a = Path(r"E:\\dramakit\\dramakit\\ai\\actions.py")
t = a.read_text(encoding="utf-8")

old = '        return f"将对《{p.get(\'project\',\'\')}》的{eps}运行阶段：{st}。会消耗算力/API额度"'
new = ('        scope = chs if p.get("chapters") else eps\n'
       '        return (f"将对《{p.get(\'project\',\'\')}》的{scope}运行阶段：{st}。"\n'
       '                f"会消耗算力/API额度")')

if old in t:
    t = t.replace(old, new, 1)
    a.write_text(t, encoding="utf-8")
    print("actions.py: 确认文案显示章节了")
else:
    # the Chinese may not round-trip through this shell; find by structure
    m = re.search(r'\n(\s*)return f"[^\n]*?\{eps\}[^\n]*?\{st\}[^\n]*?"', t)
    if not m:
        raise SystemExit("返回语句锚点没找到")
    indent = m.group(1)
    t = t[:m.start()] + (
        f'\n{indent}scope = chs if p.get("chapters") else eps'
        f'\n{indent}return (f"{{scope}} / {{st}}"'
        f' + " - costs GPU/API budget")'
    ) + t[m.end():]
    a.write_text(t, encoding="utf-8")
    print("actions.py: 返回语句改用 scope（按结构匹配）")
