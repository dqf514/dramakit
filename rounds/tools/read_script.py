"""Read one episode of the script as a person would."""
import pathlib
import sys

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.project import ProjectStore  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
store = ProjectStore.open(ROOT / "projects" / "穿成亿万总裁他前妻")
proj = store.load()
ep = next(e for e in proj.episodes if e.index == n)

print("=" * 74)
print("第%s集  《%s》" % (ep.index, ep.title))
print("  一句话：%s" % ep.logline)
print("  钩子：  %s" % ep.hook)
print("  前情：  %s" % (ep.recap or "（无）"))
for i, b in enumerate(ep.key_beats[:6], 1):
    print("  节拍%s： %s" % (i, b))
for sc in ep.scenes:
    print("-" * 74)
    print("【场%s】%s / %s / %s" % (sc.index, sc.location, sc.time_of_day, sc.mood))
    print("  %s" % (sc.summary or ""))
    for ln in sc.lines:
        kind = str(ln.kind).split(".")[-1].lower()
        tag = {"dialogue": "", "narration": "（旁白）",
               "monologue": "（内心）", "caption": "（字幕卡）"}.get(kind, "")
        print("    %-6s %s%s" % (ln.speaker, tag, ln.text))
