"""The shots that failed, put back in line.

A failed shot is not looked at again - that is the rule, so a broken
one does not cost the card twice.  But a card that was restarted is a
card that works, and the shot deserves another go.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.models import Status  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

DST = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\David\AppData\Local\Temp\opencode\opening_test"

store = ProjectStore.open(DST)
proj = store.load()
n = 0
for ep in proj.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if sh.status in (Status.FAILED, Status.PENDING) and not sh.video_path:
                print("  放回队列：%s  %s  %s秒"
                      % (sh.id[-6:], sh.action[:40], sh.duration))
                sh.status = Status.PENDING
                n += 1
store.save(proj)
print("  %d 个镜头重新排队" % n)
