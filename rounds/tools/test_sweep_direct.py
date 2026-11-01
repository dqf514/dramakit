"""Does the sweep run now, and does it settle the dead script stage?

The import was added and the call wrapped, yet the log still said Status
was undefined - so either the file on disk differs from what was checked,
or the name is resolved somewhere the import does not reach. This calls
the function the way the server does and reports what it finds.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

import dramakit.web.server as srv

src = Path(srv.__file__).read_text(encoding="utf-8")
print("server.py 里 Status 导入:", "from ..models import Status" in src)
print("settle_leftover_runs 存在:", "def settle_leftover_runs" in src)

# where is the import, relative to the class?
i = src.find("from ..models import Status")
j = src.find("class State")
k = src.find("def settle_leftover_runs")
print(f"  导入在第 {src[:i].count(chr(10)) + 1} 行")
print(f"  class State 在第 {src[:j].count(chr(10)) + 1} 行")
print(f"  settle 在第 {src[:k].count(chr(10)) + 1} 行")

print()
try:
    from dramakit.config import Config
    cfg = Config.load(Config.discover())
    root = Path(cfg.pipeline.output_dir)
    print("output_dir:", root)
    print("解析后:", root.resolve())
    st = srv.State(cfg, None, root.resolve())
    print("项目:", st.project_slugs())
    n = st.settle_leftover_runs()
    print("清理了", n, "个阶段")
except Exception as e:  # noqa: BLE001
    import traceback
    print("失败:", type(e).__name__, e)
    traceback.print_exc()

print()
d = json.loads(Path(r"E:\dramakit\projects\妖怪志\project.json").read_text(encoding="utf-8"))
print("现在:", json.dumps(d.get("stage_status", {}), ensure_ascii=False))
