"""Say what the run is about to do, and drop what is now dead.

The scope switch on the chapter list decides whether the run is about
the ticked chapters or about the whole book, so the button next to it
has to say which - otherwise a run of four chapters out of two hundred
looks the same as a run of the whole book.

The two functions that made their own runs are gone: the run button
does what they did, and the steps that are wanted are picked on the
cards.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")

# 1. the helper, right after the function that knows the ticked chapters
anchor = '''  if(!window.__chosen) window.__chosen=new Set();
  return window.__chosen;
}
'''
helper = '''  if(!window.__chosen) window.__chosen=new Set();
  window.__chapChosen=window.__chosen;
  return window.__chosen;
}
// what the run is about: the ticked chapters, or the whole book
function drawChapScope(){
  const n=window.__chapChosen?window.__chapChosen.size:0;
  const hint=document.getElementById("chapScopeHint");
  if(hint) hint.textContent=window.__chapScope?("本次做这 "+n+" 章"):"本次做整本书";
  const rs=document.getElementById("runScope");
  if(rs) rs.textContent=window.__chapScope?("· 章节 "+n+" 章"):"";
}
'''
assert anchor in text, "没找到勾选函数"
text = text.replace(anchor, helper, 1)

# 2. the chapter list redraws the hint
old = '''  const card = document.getElementById("work-chapters");
  if(card) card.style.display = "";
  _renderChapters();
}'''
new = '''  const card = document.getElementById("work-chapters");
  if(card) card.style.display = "";
  _renderChapters();
  drawChapScope();
}'''
assert old in text, "没找到章节加载"
text = text.replace(old, new, 1)

# 3. the workbench draws it too
old = '''  const rg=$("#runGo"); if(rg) rg.onclick=doRun;'''
new = '''  const rg=$("#runGo"); if(rg) rg.onclick=doRun;
  drawChapScope();'''
assert old in text, "没找到运行按钮"
text = text.replace(old, new, 1)

# 4. the dead functions: the run button does what they did
i = text.find("async function chooseChapters(){")
if i >= 0:
    j = text.index("\n}\n", i) + 3
    text = text[:i] + text[j:]
i = text.find("async function startSeason(){")
if i >= 0:
    j = text.index("\n}\n", i) + 3
    text = text[:i] + text[j:]

PATH.write_text(text, encoding="utf-8")
print("范围显示加好了，死代码清了")
