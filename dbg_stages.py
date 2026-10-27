import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore

ORDER = ["ingest", "analyze", "character", "segment", "script", "storyboard",
         "promptgen", "voice", "visual", "subtitle", "music", "precheck",
         "compose", "qc"]

for d in sorted(Path(r"E:\dramakit\projects").glob("轮次*")):
    try:
        p = ProjectStore(d).load()
    except Exception:
        print(d.name, "读取失败")
        continue
    for ep in p.episodes:
        st = ep.stage_status
        done = [s for s in ORDER if str(st.get(s, "")).endswith("done")]
        missing = [s for s in ORDER if s not in done]
        pct = round(100 * len(done) / len(ORDER))
        print(f"{d.name}: {pct}%  缺: {missing if missing else '无'}")
