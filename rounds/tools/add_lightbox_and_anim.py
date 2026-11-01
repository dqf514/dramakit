"""See a reference picture whole, and make the running stage look alive.

Two things the console could not do.

A character's reference sheet is a thumbnail beside a form, so the face
you are meant to be checking is too small to check - and a three-view
sheet is worse, since four panels share one small rectangle. Clicking a
picture now opens it over the page at whatever size the window allows,
with the character's other references one key away: left and right to
page, Esc or a click on the dark to close, and which picture you are on
shown at the top.

And a stage that runs for many minutes looked identical to a page that
had hung. The panel now pulses the word it is claiming, and carries a bar
that moves: a real one when the stage reports what it has finished, and
an honest indeterminate one when it does not - a bar that crawls is a
truer picture of "still going" than a bar stuck at zero.

The page also had two stray style closers and a style tag written inside
a style block. Harmless - <style> is raw text, so the inner tag is
literal text the CSS parser skips - but it reads as a bug and cost time
to disprove, so it is gone.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

if "openLightbox" in s:
    print("index.html: 图片查看器已存在，跳过")
    raise SystemExit(0)

# ------------------------------------------- 0. tidy the stray closers --
# the progress CSS went in with its own <style> tag, inside the block that
# was already open. The rules still applied - <style> is raw text, so the
# inner tag is literal text the CSS parser skips - but the second closer
# is dead weight and the nesting reads as a fault.
s = s.replace(""".prog-strip span{white-space:nowrap;margin-right:9px}
</style>
</style>""", """.prog-strip span{white-space:nowrap;margin-right:9px}
</style>""", 1)
s = s.replace("""
<style>
/* the progress panel: a stage that is running, and how long it has been */""",
              """
/* the progress panel: a stage that is running, and how long it has been */""", 1)

# ------------------------------------------------------------ CSS -------
css = """
/* the running stage, made to look like it is running */
@keyframes dkbreathe{0%,100%{opacity:1}50%{opacity:.45}}
.pulse{animation:dkbreathe 1.6s ease-in-out infinite}
@keyframes dkbar{0%{transform:translateX(-100%)}100%{transform:translateX(400%)}}
.prog-bar{position:relative;height:6px;border-radius:3px;overflow:hidden;
  background:var(--bg4);margin-top:10px}
.prog-bar i{display:block;height:100%;border-radius:3px;
  background:linear-gradient(90deg,var(--confirm),var(--confirm2));
  transition:width .6s ease}
/* when a stage says how much is left, the bar says so too; when it does
   not, an honest crawl is better than a bar frozen at zero */
.prog-bar.indet i{width:25%;background:linear-gradient(90deg,transparent,var(--confirm),var(--confirm2),transparent);
  animation:dkbar 1.5s linear infinite}

/* a picture, whole, over the page */
.lb-scrim{position:fixed;inset:0;background:rgba(0,0,0,.87);z-index:120;
  display:flex;align-items:center;justify-content:center;padding:18px}
.lb-box{background:var(--bg2);border:1px solid var(--line);border-radius:8px;
  width:min(1240px,97vw);max-height:97vh;display:flex;flex-direction:column;
  box-shadow:0 22px 80px rgba(0,0,0,.55)}
.lb-head{display:flex;align-items:center;gap:10px;padding:10px 14px;
  border-bottom:1px solid var(--line)}
.lb-head .t{font-weight:650}
.lb-head .n{color:var(--fg3);font-size:12px}
.lb-body{flex:1;overflow:auto;display:flex;align-items:center;justify-content:center;
  padding:14px;min-height:220px;cursor:zoom-out}
.lb-body img{max-width:100%;max-height:calc(97vh - 140px);object-fit:contain;
  border-radius:4px;background:var(--bg3)}
.lb-foot{display:flex;align-items:center;gap:12px;padding:10px 14px;
  border-top:1px solid var(--line);font-size:11.5px}
.lb-foot .btn{padding:4px 14px}
"""
i = s.find("</style>")
assert i > 0, "找不到 </style>"
s = s[:i] + css + s[i:]

# --------------------------------------- 1. the panel, alive and moving --
old_panel = '''  let item="";
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
}'''
new_panel = '''  let item="", bar="";
  if(p&&p.total){
    // the stage counts what it has finished, so the bar can be exact
    const n=Math.max(0,Math.min(100,Math.round((p.done||0)*100/p.total)));
    item=`<span class="mini muted">已完成 ${p.done||0}/${p.total} 项</span>`;
    bar=`<div class="prog-bar"><i style="width:${n}%"></i></div>`;
  }else{
    // it does not say how much is left; a bar that crawls says "still
    // going" more honestly than one stuck at zero
    bar=`<div class="prog-bar indet"><i></i></div>`;
  }
  return `<div class="card" style="margin-bottom:10px;border-color:var(--confirm)">
    <div style="display:flex;align-items:center;gap:9px">
      <span class="spin"></span>
      <b>${esc(zh)}</b>
      <span class="mini pulse" style="color:var(--confirm)">● 进行中</span>
      ${item}
      <span style="flex:1"></span>
      ${ms==null?"":`<span class="mini muted">已运行 ${fmtDur(ms)}</span>`}
    </div>
    ${hint?`<div class="muted" style="font-size:11.5px;margin-top:6px">${esc(hint)}</div>`:""}
    ${bar}
    <div class="prog-strip">${strip}</div>
  </div>`;
}'''
assert old_panel in s, "进度面板锚点没找到"
s = s.replace(old_panel, new_panel, 1)

# ------------------------------------------- 2. the viewer, and paging --
js = '''
<div id="lightboxRoot"></div>
<script>
// ---------- see a picture whole ----------
// A reference sheet is a thumbnail beside a form, and a face you are meant
// to be checking has to be checked. This opens it over the page, with the
// character's other references a key away.
let lightbox={imgs:[],i:0,label:""};
function openLightbox(imgs,i,label){
  const list=(imgs||[]).filter(Boolean);
  if(!list.length) return;
  lightbox={imgs:list,i:Math.max(0,Math.min(i||0,list.length-1)),label:label||""};
  renderLightbox();
  document.addEventListener("keydown",lightboxKeys);
}
function closeLightbox(){
  const r=document.getElementById("lightboxRoot");
  if(r) r.innerHTML="";
  document.removeEventListener("keydown",lightboxKeys);
}
function lightboxStep(d){
  const n=lightbox.i+d;
  if(n<0||n>=lightbox.imgs.length) return;
  lightbox.i=n;
  renderLightbox();
}
function lightboxKeys(e){
  if(e.key==="Escape") closeLightbox();
  else if(e.key==="ArrowLeft") lightboxStep(-1);
  else if(e.key==="ArrowRight") lightboxStep(1);
}
function renderLightbox(){
  const root=document.getElementById("lightboxRoot");
  if(!root) return;
  const {imgs,i,label}=lightbox;
  const many=imgs.length>1;
  root.innerHTML=`<div class="lb-scrim" onclick="if(event.target===this)closeLightbox()">
    <div class="lb-box">
      <div class="lb-head">
        <span class="t">${esc(label)}</span>
        ${many?`<span class="n">${i+1} / ${imgs.length}</span>`:""}
        <span style="flex:1"></span>
        <button class="btn ghost" onclick="closeLightbox()">✕</button>
      </div>
      <div class="lb-body" onclick="closeLightbox()">
        <img src="${imgs[i]}" alt="">
      </div>
      <div class="lb-foot">
        <button class="btn" ${i<=0?"disabled":""} onclick="event.stopPropagation();lightboxStep(-1)">← 上一张</button>
        <span class="muted">${many?"← → 翻页 · ":""}点击空白处或 Esc 关闭</span>
        <span style="flex:1"></span>
        <button class="btn" ${i>=imgs.length-1?"disabled":""} onclick="event.stopPropagation();lightboxStep(1)">下一张 →</button>
      </div>
    </div></div>`;
}
</script>
'''
j = s.find("</body>")
assert j > 0, "找不到 </body>"
s = s[:j] + js + s[j:]

# --------------------------------- 3. the cast page points at the viewer --
old_map = '''  const cards=chars.map((c,i)=>{
    const sheet=c.ref_sheet_url||c.ref_urls&&c.ref_urls[0]||"";'''
new_map = '''  // every picture the character has, in one list the viewer can walk
  window.__castImgs={};
  const cards=chars.map((c,i)=>{
    const imgs=[...new Set([c.ref_sheet_url||"",...(c.ref_urls||[])])].filter(Boolean);
    window.__castImgs[c.name]=imgs;
    const sheet=imgs[0]||"";'''
assert old_map in s, "角色卡锚点没找到"
s = s.replace(old_map, new_map, 1)

old_reflist = '''<div class="reflist">${(c.ref_urls||[]).slice(0,5).map(u=>`<img src="${u}" loading="lazy">`).join("")}</div>'''
new_reflist = '''<div class="reflist">${imgs.slice(0,5).map((u,k)=>`<img src="${u}" loading="lazy" data-i="${k}">`).join("")}</div>'''
assert old_reflist in s, "参考图列表锚点没找到"
s = s.replace(old_reflist, new_reflist, 1)

# the big sheet becomes clickable too
old_big = '''<div class="ref">${sheet?`<img src="${sheet}" loading="lazy">`'''
new_big = '''<div class="ref">${sheet?`<img src="${sheet}" loading="lazy" data-i="0">`'''
assert old_big in s, "主参考图锚点没找到"
s = s.replace(old_big, new_big, 1)

# and the handler, after the cast page draws
old_click = '''function renderCast(){'''
new_click = '''function wireCastViewer(){
  // delegated, so a re-render does not need rewiring each picture
  $$("#page-cast .castcard img[data-i]").forEach(img=>{
    img.style.cursor="zoom-in";
    img.onclick=()=>{
      const card=img.closest(".castcard");
      const name=card?card.dataset.name:"";
      const list=(window.__castImgs||{})[name]||[];
      openLightbox(list, Number(img.dataset.i)||0, name||"参考图");
    };
  });
}
function renderCast(){'''
assert old_click in s, "renderCast 锚点没找到"
s = s.replace(old_click, new_click, 1)

# and call it once the cards are on the page
old_tail = '''        else toast("生成失败："+esc((res&&res.error)||""),"err",6000);
      });
    };
  });
}'''
new_tail = '''        else toast("生成失败："+esc((res&&res.error)||""),"err",6000);
      });
    };
  });
  wireCastViewer();
}'''
assert old_tail in s, "renderCast 结尾锚点没找到"
s = s.replace(old_tail, new_tail, 1)

p.write_text(s, encoding="utf-8")
print("index.html: 角色照片可点开放大、可翻页；进行中有了呼吸和流动的进度条")
print("  · 左右方向键翻页，Esc 或点空白关闭")
print("  · 有总量的阶段走真实百分比，没有的走不确定进度条（诚实的爬动）")
print("  · 清掉了两个多余的 </style> 和一个写在 style 里的 <style>")
