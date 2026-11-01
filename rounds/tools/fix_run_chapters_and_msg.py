"""The direct run endpoint has to carry chapters too, and say how long a stop takes.

_api_run built its own parameter list, and chapters were added to the
action's spec rather than to that list - so a plan sent straight to
/api/run with chapters had them dropped on the floor, and only the AI path
honoured them. The list now carries what the action declares.

The stop button also claimed it would stop at the next episode. It stops
when the current call returns, which for a model call with retries is
about a minute - so the message says that, because a promise the code
cannot keep is worse than an honest one.
"""
from pathlib import Path

# ------------------------------------- 1. _api_run carries chapters ------
s = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
t = s.read_text(encoding="utf-8")

old = '''            params = {
                "project": body.get("project", ""),
                "episodes": body.get("episodes", []),
                "stages": body.get("stages", []),
                "overrides": body.get("overrides", {}),
                "season": body.get("season") or None,
            }'''
new = '''            params = {
                "project": body.get("project", ""),
                # chapters are the input: naming them is how a run is told
                # to make part of a book rather than all of it
                "chapters": body.get("chapters", []),
                "episodes": body.get("episodes", []),
                "stages": body.get("stages", []),
                "overrides": body.get("overrides", {}),
                "season": body.get("season") or None,
            }'''
assert old in t, "_api_run 的 params 锚点没找到"
t = t.replace(old, new, 1)
s.write_text(t, encoding="utf-8")
print("server.py: /api/run 现在接受 chapters")

# ---------------------------------- 2. the button tells the truth --------
h = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
p = h.read_text(encoding="utf-8")

old_msg = '  toast("已请求停止，将在当前这一集结束后停下","",4000);'
new_msg = ('  toast("已请求停止：当前这一步的调用结束后停下（约 1 分钟内），"\n'
           '        "已完成的保留","",5000);')
if old_msg in p:
    p = p.replace(old_msg, new_msg, 1)
    h.write_text(p, encoding="utf-8")
    print("index.html: 停止提示说实话了")
else:
    print("index.html: 提示锚点没找到（跳过）")

# ---------------------------------- 3. the title says it too -------------
old_title = 'title="在下一集/下一阶段停下，已完成的保留"'
new_title = 'title="当前这一步的调用结束后停下（约 1 分钟内），已完成的保留"'
if old_title in p:
    p = p.replace(old_title, new_title, 1)
    h.write_text(p, encoding="utf-8")
    print("index.html: 按钮提示也改了")
