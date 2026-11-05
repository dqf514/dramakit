"""One button to start the work.

The workbench had four ways to start: a button that ran the whole
pipeline, a button that ran the steps you had picked, a button that made
a new season out of the chapters you had ticked, and a button that did
only the segmentation and the script for them.  One of them did not
even start anything - the "run the whole flow" button only ticked every
step off.

What is left is one button and three choices, all of them already
there: which steps (the cards), which project and episodes (the bar),
and which chapters (the tick list - with a switch saying whether the
run is about those chapters or about the whole book).
"""
import pathlib
import re

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")


def sub(pattern, repl, what, count=1):
    global text
    new, n = re.subn(pattern, repl, text, count=count)
    assert n == count, "没找到：%s" % what
    text = new


# 1. the chapter panel: the two run buttons become a scope switch
sub(r'\n\s*<div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap">\s*'
    r'<button class="btn go"[^>]*data-chap="season">[^<]*</button>\s*'
    r'<button class="btn confirm"[^>]*data-chap="script">[^<]*</button>\s*</div>',
    """
        <div class="chap-tools" style="margin-bottom:4px">
          <label class="mini" style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" id="chapScope" ${window.__chapScope?"checked":""}>
            <span>本次只做勾选的章节</span>
          </label>
          <span class="muted" id="chapScopeHint" style="font-size:12px"></span>
          <span class="grow"></span>
        </div>""",
    "章节面板的两个按钮")

# 2. the top bar: the button that only ticked the steps off
sub(r'\n\s*<button class="btn go" data-act="run-all">[^<]*</button>',
    "",
    "跑完整流程")

# 3. the run bar: one button, and it says what it will do
sub(r'<button class="btn go" id="runGo">\$\{mark\("▶"\)\} 开始运行</button>',
    '<button class="btn go" id="runGo">${mark("▶")} 开始</button>',
    "开始运行")
sub(r'<button class="btn ghost sm" id="runAll">全选</button>',
    '<button class="btn ghost sm" id="runAll">全选步骤</button>',
    "全选")
sub(r'<span class="muted" id="runStat" style="font-size:12px">\$\{esc\(selText\)\}</span>',
    '<span class="muted" id="runStat" style="font-size:12px">${esc(selText)}</span>\n'
    '            <span class="muted" id="runScope" style="font-size:12px"></span>',
    "runStat")

# 4. the handlers
sub(r'\n\s*if\(a==="run-all"\)\{[^}]*\}\n\s*else if\(a==="go-board"\)',
    '\n    if(a==="go-board")',
    "run-all 的处理")
sub(r'\n\s*else if\(a==="mode"\) toggleChapMode\(\);\n\s*else if\(a==="season"\) startSeason\(\);\n\s*else if\(a==="script"\) chooseChapters\(\);\n\s*\}\);',
    """
    else if(a==="mode") toggleChapMode();
  });
  const cs=$("#chapScope"); if(cs) cs.onchange=()=>{
    window.__chapScope=cs.checked;
    renderFlow();
  };""",
    "章节按钮的处理")

# 5. the run: what it will do
sub(r'  if\(!body\.stages\.length\)\{ toast\("至少选一个阶段","err"\); return; \}',
    """  if(!body.stages.length){ toast("至少选一个阶段","err"); return; }
  // the chapters, when the run is about the ticked ones and not the
  // whole book
  if(window.__chapScope){
    const chosen=Array.from(_chapChosenSet());
    if(!chosen.length){ toast("勾了「只做选中的章节」，但一章都没勾","err"); return; }
    body.chapters=chosen;
    body.season=window.__nextSeason||1;
    const r=await postJSON("/api/chapters/choose",{project:body.project,chosen:chosen});
    if(!r||!r.ok){ toast("保存选章失败："+esc((r&&r.error)||"未知错误"),"err"); return; }
  }""",
    "doRun")

PATH.write_text(text, encoding="utf-8")
print("控制台整合好了")
