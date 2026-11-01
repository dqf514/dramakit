"""A chapter reader for the workbench: click a chapter, read the prose.

A catalogue of numbers and titles is not a story.  So a click on a chapter
row or its tile opens a reader over the page - the chapter's own text,
paged so a 3000-word chapter is not a wall - with the previous and next
chapter a click away, so you can read through the volume without going
back to the list.

The reader holds no state of its own: it asks the server for the text of
the chapter by index, and the server decides which file that is.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\web\static\index.html")
s = p.read_text(encoding="utf-8")

if "openReader" in s:
    print("index.html: 阅读器已存在，跳过")
    raise SystemExit(0)

# ---- CSS: an overlay that sits over the page, and a readable column ----
css = """
<style>
/* the reader: a scrim over the page, a sheet of paper on top of it */
.rd-scrim{position:fixed;inset:0;background:var(--scrim);z-index:80;
  display:flex;align-items:center;justify-content:center;padding:24px}
.rd-sheet{background:var(--bg2);border:1px solid var(--line);border-radius:8px;
  width:min(760px,100%);max-height:100%;display:flex;flex-direction:column;
  box-shadow:0 18px 60px var(--shadow)}
.rd-head{display:flex;align-items:center;gap:10px;padding:12px 16px;
  border-bottom:1px solid var(--line)}
.rd-head .rd-t{font-weight:650;font-size:14px}
.rd-head .rd-v{color:var(--fg3);font-size:11.5px}
.rd-body{overflow:auto;padding:18px 26px;line-height:1.95;font-size:14.5px;
  white-space:pre-wrap;color:var(--fg)}
.rd-foot{display:flex;align-items:center;gap:10px;padding:10px 16px;
  border-top:1px solid var(--line);color:var(--fg3);font-size:11.5px}
.rd-foot .btn{padding:4px 12px;font-size:12px}
</style>
"""
i = s.find("</style>")
assert i > 0, "找不到 </style>"
s = s[:i] + css + s[i:]

# ---- HTML: the overlay container, appended to <body> ----
overlay = '''
<div id="readerRoot"></div>
'''
j = s.find("</body>")
assert j > 0, "找不到 </body>"
s = s[:j] + overlay + s[j:]

# ---- JS: open the reader, page it, walk the volume ----
js = '''
<script>
// ---- chapter reader ----
function _chapByIndex(idx){
  return (window.__chapters||[]).find(c=>c.index===idx) || null;
}
async function openReader(idx){
  const slug=S.current;
  const root=document.getElementById("readerRoot");
  if(!root) return;
  // draw the shell first so the click feels instant, then fill it
  root.innerHTML='<div class="rd-scrim" onclick="if(event.target===this)closeReader()">'+
    '<div class="rd-sheet">'+
      '<div class="rd-head">'+
        '<span class="rd-t" id="rdTitle">读取中…</span>'+
        '<span class="rd-v" id="rdVol"></span>'+
        '<span style="flex:1"></span>'+
        '<span class="rd-v" id="rdPos"></span>'+
        '<button class="btn ghost" onclick="closeReader()" title="关闭 (Esc)">✕</button>'+
      '</div>'+
      '<div class="rd-body" id="rdBody">正在读取正文…</div>'+
      '<div class="rd-foot">'+
        '<button class="btn" id="rdPrev" onclick="_rdStep(-1)">← 上一章</button>'+
        '<button class="btn" id="rdNext" onclick="_rdStep(1)">下一章 →</button>'+
        '<span style="flex:1"></span>'+
        '<span id="rdMeta"></span>'+
      '</div>'+
    '</div></div>';
  window.__rdIdx=idx;
  document.addEventListener("keydown", _rdKey);

  const r=await postJSON("/api/chapter/read",{project:slug,chapter:idx});
  if(!r||!r.ok){
    const b=document.getElementById("rdBody");
    if(b) b.innerHTML='<span class="muted">读不到这一章：'+esc((r&&r.error)||"未知错误")+'</span>';
    return;
  }
  const set=(id,v)=>{const e=document.getElementById(id); if(e) e.textContent=v||"";};
  set("rdTitle","第"+r.index+"章 "+(r.title||""));
  set("rdVol", r.volume||"");
  set("rdBody", r.text||"");
  set("rdMeta", Math.round((r.chars||0)/1000)+"k 字");
  _rdSyncNav();
}
function _rdSyncNav(){
  // grey out the ends of the volume, and say where you are
  const list=window.__chapters||[];
  const pos=list.findIndex(c=>c.index===window.__rdIdx);
  const set=(id,dis)=>{const e=document.getElementById(id); if(e) e.disabled=!!dis;};
  set("rdPrev", pos<=0);
  set("rdNext", pos<0 || pos>=list.length-1);
  const e=document.getElementById("rdPos");
  if(e && pos>=0) e.textContent="第 "+(pos+1)+" / "+list.length+" 章";
}
function _rdStep(dir){
  const list=window.__chapters||[];
  const pos=list.findIndex(c=>c.index===window.__rdIdx);
  const nx=list[pos+dir];
  if(nx) openReader(nx.index);
}
function _rdKey(e){
  if(e.key==="Escape"){ closeReader(); return; }
  if(e.key==="ArrowLeft") _rdStep(-1);
  if(e.key==="ArrowRight") _rdStep(1);
}
function closeReader(){
  const root=document.getElementById("readerRoot");
  if(root) root.innerHTML="";
  document.removeEventListener("keydown", _rdKey);
}
</script>
'''
k = s.find("</body>")
s = s[:k] + js + s[k:]

# ---- wire the clicks: a title opens the reader, without disturbing the pick ----
# list rows: make the chapter name a clickable title
old_row = ("'<b>第'+c.index+'章</b> '+esc(c.title||'')+' ' +")
new_row = ("'<b class=\"rd-open\" onclick=\"event.stopPropagation();openReader('+c.index+')\" ' +\n"
           "        'style=\"cursor:pointer\" title=\"点击阅读\">第'+c.index+'章 '+esc(c.title||'')+'</b> ' +")
assert old_row in s, "找不到列表行锚点"
s = s.replace(old_row, new_row, 1)

# icon tiles: a click reads, a small check corner picks - so the tile can do both
old_tile_onclick = 'onclick="_chapTile(this)">'
new_tile_onclick = 'onclick="openReader(\'+c.index+\')">'
assert old_tile_onclick in s, "找不到图标块锚点"
s = s.replace(old_tile_onclick, new_tile_onclick, 1)

# the tile's pick corner: a small checkbox-like tick you can toggle
old_tick = ("'<span class=\"tick\">✓</span>' +")
new_tick = ("<span class=\"tick\" onclick=\"event.stopPropagation();_chapTile(this.parentNode)\" ' +\n"
            "        'title=\"选中 / 取消\">'+(chosen.has(c.index)?'✓':'')+'</span>' +")
assert old_tick in s, "找不到 tick 锚点"
s = s.replace(old_tick, new_tick, 1)

p.write_text(s, encoding="utf-8")
print("index.html: 章节阅读器做好了（点标题或图标块阅读，←/→ 翻章，Esc 关闭）")
