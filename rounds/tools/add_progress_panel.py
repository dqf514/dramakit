"""Show what the后台 is doing, without touching what it is doing.

A task was submitted and the workbench said nothing. Two reasons, both in
the page.

runningStageName() looked only at per-episode stage statuses, but ingest,
analyze and character belong to the project and to no episode - so while
the cast was being dressed the page believed nothing was running.

startProgressPoll() asked whether anything was running before it fetched
anything, and the only way to learn that is to fetch. A page that waits
for news it will not request never gets it.

The fix keeps to the page. A panel above the workbench shows the stage
that is running, what that stage is for, how long it has been at it, and
the pipeline lit up to the current step. The poll runs whenever a project
is open and updates that panel in place rather than redrawing the
workbench, so a long chapter list keeps its scroll and its ticks. Nothing
is restarted, and nothing already running is disturbed.
"""
import re
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

if "workProgressHtml" in s:
    print("index.html: 进度面板已存在，跳过")
    raise SystemExit(0)

# ---------------------------------------------------------------- CSS ----
css = """
<style>
/* the progress panel: a stage that is running, and how long it has been */
@keyframes dkspin{to{transform:rotate(360deg)}}
.spin{display:inline-block;width:11px;height:11px;border:2px solid var(--line);
  border-top-color:var(--confirm);border-radius:50%;
  animation:dkspin .9s linear infinite;vertical-align:-1px}
#progressSlot:empty{display:none}
.prog-strip{margin-top:9px;font-size:11.5px;line-height:2}
.prog-strip span{white-space:nowrap;margin-right:9px}
</style>
"""
i = s.find("</style>")
assert i > 0, "找不到 </style>"
s = s[:i] + css + s[i:]

# ------------------------------------------- 1. which stage is running ----
old_run = '''function runningStageName(){
  const eps=(S.detail&&S.detail.episodes)||[];
  let runningStage="";
  for(const ep of eps){ for(const s of STAGES){ if((ep.stage_status||{})[s]==="running") runningStage=s; } }
  return runningStage;
}'''
new_run = '''function runningStageName(){
  // The project's own stages come first: ingest, analyze and character
  // belong to the project, not to any episode, so a page that looks only
  // at the episodes reports nothing running while the cast is being
  // dressed - which is most of the wait.
  const proj=(S.detail&&S.detail.stage_status)||{};
  for(const s of STAGES){ if(proj[s]==="running") return s; }
  const eps=(S.detail&&S.detail.episodes)||[];
  for(const ep of eps){ for(const s of STAGES){ if((ep.stage_status||{})[s]==="running") return s; } }
  return "";
}

// how long this stage has been running, as the page has seen it
let stageWatch={stage:"",since:0};
function stageElapsed(){
  const st=runningStageName();
  if(!st){ stageWatch={stage:"",since:0}; return null; }
  if(stageWatch.stage!==st){ stageWatch={stage:st,since:Date.now()}; }
  return Date.now()-stageWatch.since;
}
function fmtDur(ms){
  const t=Math.max(0,Math.round(ms/1000));
  const h=Math.floor(t/3600), m=Math.floor(t%3600/60), sec=t%60;
  if(h) return h+" 时 "+m+" 分";
  if(m) return m+" 分 "+sec+" 秒";
  return sec+" 秒";
}

// the panel: which stage, what it is for, and the pipeline lit to here
function workProgressHtml(){
  const st=runningStageName();
  if(!st) return "";
  const zh=STAGE_ZH[st]||st;
  const hint=STAGE_HINT[st]||"";
  const p=(S.progress||{})[st];
  const ms=stageElapsed();
  const strip=STAGES.map((x,i)=>{
    const v=stageState(x);
    const mark=v==="done"?"●":v==="running"?"◐":"○";
    const col=v==="done"?"var(--go2)":v==="running"?"var(--confirm)":"var(--fg3)";
    return `<span style="color:${col}" title="${esc(STAGE_HINT[x]||STAGE_ZH[x])}">${mark} ${i+1} ${esc(STAGE_ZH[x])}</span>`;
  }).join("");
  let item="";
  if(p&&p.total) item=`<span class="mini muted">已完成 ${p.done||0}/${p.total} 项</span>`;
  return `<div class="card" style="margin-bottom:10px;border-color:var(--confirm)">
    <div style="display:flex;align-items:center;gap:9px">
      <span class="spin"></span>
      <b>${esc(zh)}</b>
      <span class="mini" style="color:var(--confirm)">进行中</span>
      ${item}
      <span style="flex:1"></span>
      ${ms==null?"":`<span class="mini muted">已运行 ${fmtDur(ms)}</span>`}
    </div>
    ${hint?`<div class="muted" style="font-size:11.5px;margin-top:6px">${esc(hint)}</div>`:""}
    <div class="prog-strip">${strip}</div>
  </div>`;
}

// update the panel where it stands: the workbench is not redrawn, so a
// long chapter list keeps its scroll and its ticks while this moves
function updateProgressPanel(){
  const slot=document.getElementById("progressSlot");
  if(!slot) return false;
  slot.innerHTML=workProgressHtml();
  return true;
}'''
assert old_run in s, "runningStageName 锚点没找到"
s = s.replace(old_run, new_run, 1)

# --------------------------------------------- 2. a place for the panel --
old_slot = "  box.innerHTML=`<div class=\"wb-layout\">"
new_slot = ("  box.innerHTML=`<div id=\"progressSlot\">${workProgressHtml()}</div>\n"
            "    <div class=\"wb-layout\">")
assert old_slot in s, "工作台 innerHTML 锚点没找到"
s = s.replace(old_slot, new_slot, 1)

# --------------------------------------------------- 3. the poll actually
# match the poll by structure: find the function and rewrite its body
m = re.search(r"function startProgressPoll\(\)\{.*?\n\s*\}, \d+\);", s, re.S)
assert m, "找不到 startProgressPoll"
new_poll = '''function startProgressPoll(){
  if(progressPollTimer) clearInterval(progressPollTimer);
  progressPollTimer=setInterval(async ()=>{
    if(!S.current) return;
    // Always ask. The old poll checked whether anything was running before
    // it fetched, and the only way to learn that is to fetch - so a task
    // submitted after the page loaded was never seen, and the workbench
    // stayed silent for the whole run.
    try{
      const d=await getJSON("/api/projects/"+encodeURIComponent(S.current));
      if(!d||!d.ok) return;
      S.detail=d;
      const pr=await getJSON("/api/progress?project="+encodeURIComponent(S.current));
      if(pr&&pr.ok) S.progress=pr.progress||{};
      // the panel is updated where it stands: redrawing the workbench
      // would reset the scroll of a chapter list the user is reading
      updateProgressPanel();
      renderHeader(); renderProjects();
    }catch(e){/* 网络瞬断 */}
  }, 4000);'''
s = s[:m.start()] + new_poll + s[m.end():]

p.write_text(s, encoding="utf-8")
print("index.html: 工作台有进度面板了")
print("  · 项目级阶段也算在跑（ingest/analyze/character 不属于任何一集）")
print("  · 轮询一直跑，不再等一个它自己拿不到的信号")
print("  · 面板就地更新，不重绘工作台（章节列表的滚动和勾选不丢）")
