"""A plan that names its chapters, in the language the console speaks.

The confirm dialog lost its Chinese when a structural fallback replaced a
line it could not match by text, and the chapter range was written in
English beside it. Both are restored: the message names the project, the
chapters the book will be cut from, and the stages that will run - the
things a user checks before agreeing to spend anything.
"""
from pathlib import Path

a = Path(r"E:\\dramakit\\dramakit\\ai\\actions.py")
t = a.read_text(encoding="utf-8")

old_chs = '''        chs = (f"{min(p['chapters'])}-{max(p['chapters'])} (of {len(p['chapters'])})" if p.get("chapters") else "all chapters")'''
new_chs = '''        chs = (f"第{min(p['chapters'])}~{max(p['chapters'])}章（共{len(p['chapters'])}章）"
               if p.get("chapters") else "全部章节")'''
assert old_chs in t, "chs 那行没找到"
t = t.replace(old_chs, new_chs, 1)

old_ret = '''        return (f"{scope} / {st}" + " - costs GPU/API budget")'''
new_ret = '''        return (f"将对《{p.get('project','')}》的{scope}运行阶段：{st}。"
                f"会消耗算力/API额度")'''
assert old_ret in t, "返回那行没找到"
t = t.replace(old_ret, new_ret, 1)

a.write_text(t, encoding="utf-8")
print("actions.py: 确认文案恢复中文，且显示章节范围")
