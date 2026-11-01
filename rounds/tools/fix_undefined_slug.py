"""renderWorkbench referenced a variable that did not exist.

After drawing the page it ran `if(slug) loadChapters(slug)` - but there is
no `slug` in renderWorkbench; the only one is a local inside
chooseChapters.  So the line threw a ReferenceError, loadChapters never
ran, and the chapter card - drawn with display:none - stayed invisible.
The workbench looked empty even though the catalog was there.

Use S.current, the project that is actually open.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

old = "  if(slug) loadChapters(slug).catch(function(){});"
new = "  if(S.current) loadChapters(S.current).catch(function(){});"

if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("index.html: renderWorkbench 改用 S.current")
else:
    print("index.html: 没找到那行，检查实际写法")
    i = s.find("loadChapters(")
    print(repr(s[max(0, i - 40):i + 60]))
