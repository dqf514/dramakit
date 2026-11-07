import pathlib
import re
from jinja2 import Environment

t = pathlib.Path(r"E:\dramakit\dramakit\prompts\templates.py").read_text(encoding="utf-8")
env = Environment()
for name in ("SCRIPT_PLAN_USER", "SCRIPT_SCENE_USER", "STORYBOARD_USER",
             "SCRIPT_USER"):
    m = re.search(name + r' = """(.*?)"""', t, re.S)
    if not m:
        print("  %s 没找到" % name)
        continue
    try:
        env.parse(m.group(1))
        print("  %s 能解析" % name)
    except Exception as e:
        print("  %s 报错: %s" % (name, str(e)[:140]))
