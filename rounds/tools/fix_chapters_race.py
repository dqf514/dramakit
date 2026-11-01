"""The chapters go into the page after the page is built.

The workbench is drawn from scratch every time a project opens, and the
chapters were fetched at the same time - so the fetch finished into a
card that had already been replaced, and the list never showed.  The
fetch is asked for by the drawing now, after the card is there.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

old = "box.innerHTML=`${chapterHtml}\n"
new = "box.innerHTML=`${chapterHtml}\n"
# the drawing is the one that asks for the chapters
old2 = "  if(slug) loadChapters(slug).catch(function(){});"
if old2 in s:
    print("index.html: 已经改过了")
else:
    i = s.find("box.innerHTML=`${chapterHtml}")
    assert i > 0, "没找到 chapterHtml 的使用"
    # find the end of that statement's template literal: the closing backtick+;
    j = s.find("`;", i)
    assert j > i, "没找到语句结尾"
    s = s[:j + 2] + "\n  if(slug) loadChapters(slug).catch(function(){});" + s[j + 2:]
    p.write_text(s, encoding="utf-8")
    print("index.html: 工作台画完就加载章节")
