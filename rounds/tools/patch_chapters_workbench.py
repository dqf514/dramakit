"""The chapter directory belongs where the user is: the workbench.

The card was in the guide page, which is where a project is created and
not where a project is worked on.  Open the project and the chapters were
nowhere to be seen, so the only thing to do was press a button and hope
the pipeline was on the chapter you meant.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

# 1. the card goes into the workbench, above the episodes
if "chapterBox" not in s:
    old = """  const epHtml=eps.map(ep=>`<div class="epcard" data-ep="${ep.index}">"""
    new = """  const chapterHtml =
    `<div class="card" id="work-chapters" style="display:none;margin-bottom:10px">
       <div style="display:flex;align-items:center;gap:8px">
         <b>章节目录</b>
         <span class="muted" id="chapterHint" style="font-size:11.5px"></span>
         <span style="flex:1"></span>
         <input type="number" id="epWanted" value="1" min="1" max="50"
                style="width:56px" title="生成几集">
         <button class="btn go" onclick="chooseChapters()">按选中章节开始</button>
       </div>
       <div id="chapterList" style="max-height:320px;overflow:auto;margin-top:8px"></div>
     </div>`;
  const epHtml=eps.map(ep=>`<div class="epcard" data-ep="${ep.index}">"""
    assert old in s, "工作台锚点没找到"
    s = s.replace(old, new, 1)

    # and put it in the page
    old2 = """  box.innerHTML=`"""
    # the workbench's innerHTML assignment: insert the chapter card at its head
    i = s.find("function renderWorkbench()")
    j = s.find("box.innerHTML=`", i)
    assert j > 0, "没找到工作台的 innerHTML"
    s = s[:j + len("box.innerHTML=`")] + "${chapterHtml}" + s[j + len("box.innerHTML=`"):]

p.write_text(s, encoding="utf-8")
print("index.html: 章节目录挪到工作台")
