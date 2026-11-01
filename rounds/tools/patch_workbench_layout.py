"""The chapter directory gets its own column, an icon mode, and select-all.

449 chapters in one scrolling list is unusable: you cannot see the story,
and clicking through them is a chore.  So the workbench becomes a two
column layout - the project on the left, the chapter directory pinned to
the right - and the directory has two modes: a list (as it was) and a
compact icon grid where every chapter is a small numbered tile you can
scan and toggle.  Select all / select none sit at the top, and the count
follows as you click.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- CSS ----
css = """
<style>
/* workbench: main column + chapter rail on the right */
.wb-layout{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:14px;align-items:start}
.wb-main{min-width:0}
.wb-rail{position:sticky;top:0;min-width:0}
@media (max-width:1100px){.wb-layout{grid-template-columns:minmax(0,1fr)}
  .wb-rail{position:static}}

/* the chapter rail card */
#work-chapters{margin-bottom:0}
.chap-tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0}
.chap-tools .btn{padding:3px 9px;font-size:11.5px}
.chap-tools .grow{flex:1}
.chap-body{max-height:calc(100vh - 210px);overflow:auto;margin-top:6px}

/* icon mode: a tile per chapter, scannable at a glance */
.chap-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(58px,1fr));gap:5px}
.chap-tile{position:relative;border:1px solid var(--line);background:var(--bg3);
  border-radius:var(--r);padding:6px 3px;text-align:center;cursor:pointer;
  font-size:10.5px;line-height:1.25;user-select:none;transition:.12s}
.chap-tile .cn{font-weight:650;color:var(--fg2);display:block}
.chap-tile .ck{color:var(--fg3);font-size:9px;display:block;margin-top:1px}
.chap-tile.on{background:var(--pcard-on);border-color:var(--proj-on-line)}
.chap-tile.on .cn{color:var(--confirm)}
.chap-tile:hover{border-color:var(--confirm)}
.chap-tile .tick{position:absolute;top:1px;right:3px;font-size:9px;color:var(--confirm);opacity:0}
.chap-tile.on .tick{opacity:1}
.chap-vol{grid-column:1/-1;font-size:10.5px;color:var(--fg3);margin:6px 0 2px;
  border-bottom:1px solid var(--line);padding-bottom:2px;font-weight:600}
</style>
"""
i = s.find("</style>")
assert i > 0, "没找到 </style>"
s = s[:i] + css + s[i:]

# --------------------------------------------- workbench layout HTML ----
# wrap the main body in a grid, move the chapter card into the right rail
old_hero = '  box.innerHTML=`${chapterHtml}\n    <div class="hero">'
new_hero = '''  box.innerHTML=`<div class="wb-layout">
    <div class="wb-main">
    <div class="hero">'''
assert old_hero in s, "hero 锚点没找到"
s = s.replace(old_hero, new_hero, 1)

# close wb-main and drop the rail in right after the episodes grid
old_tail = """    <h2 class="page" style="font-size:14px;margin:14px 0 8px">分集</h2>
    <div class="epgrid">${epHtml||'<div class="empty">还没有分集，先跑导入/分析</div>'}</div>`;
  if(S.current) loadChapters(S.current).catch(function(){});"""
new_tail = """    <h2 class="page" style="font-size:14px;margin:14px 0 8px">分集</h2>
    <div class="epgrid">${epHtml||'<div class="empty">还没有分集，先跑导入/分析</div>'}</div>
    </div>
    <div class="wb-rail">${chapterHtml}</div>
  </div>`;
  if(S.current) loadChapters(S.current).catch(function(){});"""
assert old_tail in s, "分集尾部锚点没找到"
s = s.replace(old_tail, new_tail, 1)

# the chapter card: add mode toggle + select all/none, give the body an id
old_card = '''  const chapterHtml =
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
     </div>`;'''
new_card = '''  const chapterHtml =
    `<div class="card" id="work-chapters" style="display:none">
       <div style="display:flex;align-items:center;gap:8px">
         <b>章节目录</b>
         <span class="muted" id="chapterHint" style="font-size:11.5px"></span>
         <span style="flex:1"></span>
         <span class="mini" id="chapMode" style="cursor:pointer;user-select:none"
               onclick="toggleChapMode()" title="切换 列表 / 图标">☰ 列表</span>
       </div>
       <div class="chap-tools">
         <button class="btn" onclick="setAllChapters(true)">全选</button>
         <button class="btn" onclick="setAllChapters(false)">全不选</button>
         <span class="grow"></span>
         <label class="mini muted">生成</label>
         <input type="number" id="epWanted" value="1" min="1" max="50"
                style="width:52px" title="生成几集">
         <label class="mini muted">集</label>
       </div>
       <button class="btn go" style="width:100%;margin-bottom:6px"
               onclick="chooseChapters()">按选中章节开始</button>
       <div class="chap-body" id="chapterList"></div>
     </div>`;'''
assert old_card in s, "章节卡片锚点没找到"
s = s.replace(old_card, new_card, 1)

# --------------------------------------------- loadChapters rewrite ----
old_load = '''async function loadChapters(slug){
  const r = await postJSON("/api/catalog",{project:slug});
  if(!r || !r.ok) return;
  window.__chapters = r.chapters || [];
  const box = document.getElementById("chapterList");
  if(!box) return;
  box.innerHTML = window.__chapters.map((c,i)=>
    '<label style="display:flex;gap:8px;align-items:center;padding:3px 0">' +
      '<input type="checkbox" data-idx="' + c.index + '" checked> ' +
      '<b>' + (c.volume||'') + ' 第' + c.index + '章</b> ' + (c.title||'') + ' ' +
      '<span class="muted">' + Math.round(c.chars/1000) + 'k 字</span>' +
    '</label>').join("") || '<div class="muted">这本书没有切出章节</div>';
  const card = document.getElementById("work-chapters");
  if(card) card.style.display = "";
  const hint = document.getElementById("chapterHint");
  if(hint) hint.textContent = "本项目共 "+window.__chapters.length+" 章" +
      "，已选 "+(window.__chosen&&window.__chosen.length||window.__chapters.length)+" 章";
}'''
new_load = '''// which chapters are picked: keep it here so switching modes keeps your picks
window.__chosen = window.__chosen || null;
window.__chapMode = window.__chapMode || "list";

function _chapChosenSet(){
  // the set of picked chapter indices, rebuilt from the DOM if we have one
  const boxes=[].slice.call(document.querySelectorAll("#chapterList input[type=checkbox]"));
  if(boxes.length){
    window.__chosen=new Set(boxes.filter(b=>b.checked).map(b=>Number(b.dataset.idx)));
  }
  if(!window.__chosen) window.__chosen=new Set();
  return window.__chosen;
}
function updateChapHint(){
  const hint=document.getElementById("chapterHint");
  if(!hint) return;
  const n=(window.__chapters||[]).length;
  const k=_chapChosenSet().size;
  hint.textContent="共 "+n+" 章 · 已选 "+k;
}
function _chapClick(idx, on){
  const set=_chapChosenSet();
  if(on) set.add(idx); else set.delete(idx);
  updateChapHint();
}
function setAllChapters(on){
  const set=_chapChosenSet();
  if(on){ (window.__chapters||[]).forEach(c=>set.add(c.index)); }
  else set.clear();
  // reflect it in whichever mode is showing
  [].slice.call(document.querySelectorAll("#chapterList input[type=checkbox]"))
    .forEach(b=>{ b.checked=on; });
  [].slice.call(document.querySelectorAll("#chapterList .chap-tile"))
    .forEach(t=>{ t.classList.toggle("on", on); });
  updateChapHint();
}
function toggleChapMode(){
  _chapChosenSet();                       // stash picks before we redraw
  window.__chapMode = window.__chapMode==="list" ? "icon" : "list";
  _renderChapters();
}
function _renderChapters(){
  const box=document.getElementById("chapterList");
  const chs=window.__chapters||[];
  if(!box) return;
  const chosen=_chapChosenSet();
  const mode=window.__chapMode;
  const lbl=document.getElementById("chapMode");
  if(lbl) lbl.textContent = mode==="list" ? "☰ 列表" : "▦ 图标";

  if(!chs.length){ box.innerHTML='<div class="muted">这本书没有切出章节</div>'; return; }

  if(mode==="list"){
    let lastVol=null, out=[];
    chs.forEach(c=>{
      if(c.volume && c.volume!==lastVol){
        out.push('<div class="chap-vol">'+esc(c.volume)+'</div>');
        lastVol=c.volume;
      }
      out.push('<label style="display:flex;gap:8px;align-items:center;padding:2px 0">' +
        '<input type="checkbox" data-idx="'+c.index+'"'+(chosen.has(c.index)?' checked':'')+
        ' onchange="_chapClick('+c.index+',this.checked)"> ' +
        '<b>第'+c.index+'章</b> '+esc(c.title||'')+' ' +
        '<span class="muted">'+Math.round(c.chars/1000)+'k 字</span></label>');
    });
    box.innerHTML=out.join("");
  } else {
    let lastVol=null, out=['<div class="chap-grid">'];
    chs.forEach(c=>{
      if(c.volume && c.volume!==lastVol){
        out.push('</div><div class="chap-vol">'+esc(c.volume)+'</div><div class="chap-grid">');
        lastVol=c.volume;
      }
      out.push('<div class="chap-tile'+(chosen.has(c.index)?' on':'')+'" '+
        'data-idx="'+c.index+'" title="第'+c.index+'章 '+esc(c.title||'')+' · '+
        Math.round(c.chars/1000)+'k 字" onclick="_chapTile(this)">' +
        '<span class="tick">✓</span>' +
        '<span class="cn">'+c.index+'</span>' +
        '<span class="ck">'+Math.round(c.chars/1000)+'k</span></div>');
    });
    out.push('</div>');
    box.innerHTML=out.join("");
  }
  updateChapHint();
}
function _chapTile(el){
  const on=!el.classList.contains("on");
  el.classList.toggle("on", on);
  _chapClick(Number(el.dataset.idx), on);
}
async function loadChapters(slug){
  const r = await postJSON("/api/catalog",{project:slug});
  if(!r || !r.ok) return;
  window.__chapters = r.chapters || [];
  window.__chosen = new Set(window.__chapters.map(c=>c.index));   // start all-on
  const card = document.getElementById("work-chapters");
  if(card) card.style.display = "";
  _renderChapters();
}'''
assert old_load in s, "loadChapters 锚点没找到"
s = s.replace(old_load, new_load, 1)

# chooseChapters reads the set instead of scraping checkboxes (works in both modes)
old_choose = '''  const boxes = [].slice.call(document.querySelectorAll("#chapterList input[type=checkbox]"));
  const chosen = boxes.filter(function(b){return b.checked;})
                      .map(function(b){return Number(b.dataset.idx);});'''
new_choose = '''  const chosen = [].slice.call(_chapChosenSet());'''
assert old_choose in s, "chooseChapters 锚点没找到"
s = s.replace(old_choose, new_choose, 1)

p.write_text(s, encoding="utf-8")
print("index.html: 工作台改成左右两列，章节目录在右侧独立列")
print("  + 全选 / 全不选")
print("  + 列表 / 图标两种模式")
print("  + 选中状态跨模式保留，计数实时更新")
