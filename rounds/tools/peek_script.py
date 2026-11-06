"""What the script stage actually wrote."""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.project import ProjectStore  # noqa: E402

store = ProjectStore.open(ROOT / "projects" / "穿成亿万总裁他前妻")
proj = store.load()
ep = proj.episodes[0]
print("=" * 72)
print("第%s集  %s" % (ep.index, ep.title))
print("  logline:", ep.logline)
print("  hook:", ep.hook)
for sc in ep.scenes[:2]:
    print("-" * 72)
    print("  场%s  %s  %s  %s" % (sc.index, sc.location, sc.time_of_day, sc.mood))
    print("  概要:", (sc.summary or "")[:300])
    for sh in sc.shots[:3]:
        print("    镜%s  %s" % (sh.id[-6:], (sh.action or "")[:220]))
        for ln in (sh.lines or [])[:3]:
            print("       %s: %s" % (ln.speaker, (ln.text or "")[:120]))
