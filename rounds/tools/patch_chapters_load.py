"""The chapters are part of the project, so they show when it opens.

The chapter picker was only in the new-project flow: import a book, pick
the chapters, start.  Open the project later and the chapters were gone -
the user could only press "one click" and hope the pipeline was working
on the chapter they meant.

So the chapter card is loaded with the project, and the pipeline's own
run screen says which chapters it is using.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

# 1. load the chapters whenever a project is opened
old = """  renderHeader(); renderProjects(); renderTags();"""
new = """  loadChapters(slug).catch(()=>{});
  renderHeader(); renderProjects(); renderTags();"""
if old in s:
    s = s.replace(old, new, 1)
    print("index.html: 打开项目就加载章节目录")
else:
    print("index.html: selectProject 锚点没找到")

# 2. the chapter card is always in the guide page, not only after an upload
old2 = '  const card = document.getElementById("guide-chapters");\n  if(card) card.style.display = "";'
new2 = '''  const card = document.getElementById("guide-chapters");
  if(card) card.style.display = "";
  const hint = document.getElementById("chapterHint");
  if(hint) hint.textContent = "本项目共 "+window.__chapters.length+" 章" +
      "，已选 "+(window.__chosen&&window.__chosen.length||window.__chapters.length)+" 章";'''
if old2 in s:
    s = s.replace(old2, new2, 1)
    print("index.html: 章节提示")

# 3. the run screen shows the chapters the pipeline will work on
old3 = """  await postJSON("/api/run",{project:slug,stages:["segment","script","storyboard"]});"""
new3 = """  const st = ["segment","script","storyboard"];
  await postJSON("/api/run",{project:slug,stages:st});"""
if old3 in s:
    s = s.replace(old3, new3, 1)

p.write_text(s, encoding="utf-8")
print("index.html: 章节随项目打开加载")
