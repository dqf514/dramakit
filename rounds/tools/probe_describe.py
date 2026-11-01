"""What does the console show the user before it runs a plan?

The plan has to name the chapters, or a misreading of "前十章" is only
discovered after the money is spent. This reads the description the
confirm dialog builds, so the chapters are visibly part of it.
"""
import inspect
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.ai import actions

fns = [n for n, o in inspect.getmembers(actions, inspect.isfunction)
       if not n.startswith("_")]
print("公开函数:", fns)

t = Path = None
from pathlib import Path as _P
src = _P(actions.__file__).read_text(encoding="utf-8")
k = src.index("eps = f")
print()
print("=== 摘要那段 ===")
print(src[k - 320:k + 320])

print()
print("=== 实际调用 ===")
for name in fns:
    if "desc" in name.lower() or "summary" in name.lower() or "message" in name.lower():
        print(f"  {name}{inspect.signature(getattr(actions, name))}")
        for raw in ({"chapters": ["1-10"]}, {"chapters": [1, 2, 3]}, {}):
            act = actions._build("run_pipeline", raw, ["测试项目"])
            try:
                print(f"    {raw} -> {getattr(actions, name)(act)}")
            except TypeError as e:
                # it may take the action's params instead
                try:
                    print(f"    {raw} -> {getattr(actions, name)(act.params)}")
                except Exception as e2:  # noqa: BLE001
                    print(f"    {raw} -> 调用失败 {e} / {e2}")
