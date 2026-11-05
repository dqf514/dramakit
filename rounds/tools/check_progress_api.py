"""Does the progress reach the console?

The tally is written by the stages, read by the api and drawn by the
page.  This puts numbers into the tally and asks the console for them,
so the chain is checked without running a whole drama.
"""
import json
import pathlib
import sys
import threading
import time
import urllib.parse
import urllib.request

sys.path.insert(0, r"E:\dramakit")

from dramakit.pipeline.progress import FILE_NAME, Progress

SLUG = "_progress_check"


def get(path):
    with urllib.request.urlopen("http://127.0.0.1:8080" + path,
                                timeout=60) as r:
        return json.loads(r.read())


def main():
    root = pathlib.Path(r"E:\dramakit\projects") / SLUG
    root.mkdir(parents=True, exist_ok=True)
    prog = Progress(root / FILE_NAME)

    # two lanes, a stage that is running, one that is done, one that failed
    prog.lane("写作", "storyboard")
    prog.lane("绘制", "visual")
    prog.begin("storyboard", 40, 4)
    prog.began("storyboard")
    prog.began("storyboard")
    prog.finished("storyboard")
    prog.begin("visual", 120, 1)
    prog.began("visual")
    prog.begin("promptgen", 150, 4)
    for _ in range(3):
        prog.began("promptgen")
    prog.finished("promptgen")
    prog.finished("promptgen", ok=False)

    d = get("/api/progress?project=" + SLUG)
    print("接口给的：")
    print("  在飞:", d.get("inflight"))
    print("  已发起:", d.get("started"), " 完成:", d.get("done"),
          " 失败:", d.get("failed"), " 共计:", d.get("total"))
    print("  道:", d.get("lanes"))
    for k, v in (d.get("stages") or {}).items():
        print("   %-12s %s" % (k, json.dumps(v, ensure_ascii=False)))

    # storyboard 1 + visual 1 + promptgen 1 are in flight
    ok = (d.get("inflight") == 3
          and d.get("started") == 6
          and d.get("done") == 2
          and d.get("failed") == 1
          and d.get("total") == 310
          and (d.get("lanes") or {}).get("写作") == "storyboard"
          and (d.get("stages") or {}).get("promptgen", {}).get("concurrency") == 4)
    print()
    print("对得上：" if ok else "对不上！")
    return 0 if ok else 1


if __name__ == "__main__":
    import pathlib
    sys.exit(main())
