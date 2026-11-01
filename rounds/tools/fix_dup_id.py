"""One chapter list, not two with the same name.

The card was in the guide page and in the workbench, both with the ids
chapterList and epWanted.  getElementById returns the first one it finds -
the guide page's, which is hidden - so the workbench's list never got
filled, and the episode count the user typed was read from the hidden
field instead.  The guide page's card is gone: the workbench is where a
project is worked on.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

start_marker = '<div class="card" id="guide-chapters"'
end_marker = '<h2 class="page" style="font-size:14px'

a = s.find(start_marker)
if a < 0:
    print("index.html: 引导页的卡片已经不在了")
else:
    b = s.find(end_marker, a)
    assert b > a, "没找到卡片结尾"
    s = s[:a] + s[b:]
    p.write_text(s, encoding="utf-8")
    print("index.html: 引导页的重复章节卡删掉了")

print("  chapterList 出现次数:", s.count('id="chapterList"'))
print("  epWanted 出现次数:", s.count('id="epWanted"'))
print("  work-chapters 出现次数:", s.count('id="work-chapters"'))
