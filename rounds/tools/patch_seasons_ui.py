"""The workbench shows the seasons, and one season is one whole run.

A long book is made a season at a time, and the page said nothing about
that: it showed a flat list of episodes and a button that started three
stages. So there was no way to see which chapters a season took, what it
produced, or where the next one should start - and no way to start a
season as a season rather than as a fragment of the pipeline.

The panel sits above the episodes. It lists each season with the chapters
it consumed and what it left behind, and the button runs the whole thing
for the chapters that are picked.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8")

# ---- 1. the seasons panel, drawn above the episodes -----------------------
old_html = '''  const epHtml=eps.map(ep=>`<div class="epcard" data-ep="${ep.index}">'''
new_html = '''  const seasonHtml =
    `<div class="card" id="work-seasons" style="display:none">
       <div style="display:flex;align-items:center;gap:8px">
         <b>制作季</b>
         <span class="muted" id="seasonHint" style="font-size:11.5px"></span>
         <span style="flex:1"></span>
         <span class="mini muted">每季完整跑一遍流水线</span>
       </div>
       <div id="seasonList" style="margin-top:8px"></div>
       <div class="muted" style="font-size:11px;margin-top:8px">
         选中章节后开始新的一季；已做过的章节不再重复，角色造型默认沿用。
       </div>
     </div>`;
  const epHtml=eps.map(ep=>`<div class="epcard" data-ep="${ep.index}">'''
assert old_html in s, "epHtml anchor not found"
s = s.replace(old_html, new_html, 1)

# ---- 2. put it in the page, above 分集 -----------------------------------
old_head = '''    <h2 class="page" style="font-size:14px;margin:14px 0 8px">分集</h2>
    <div class="epgrid">${epHtml||'<div class="empty">还没有分集，先跑导入/分析</div>'}</div>'''
new_head = '''    ${seasonHtml}
    <h2 class="page" style="font-size:14px;margin:14px 0 8px">分集</h2>
    <div class="epgrid">${epHtml||'<div class="empty">还没有分集，先跑导入/分析</div>'}</div>'''
assert old_head in s, "episodes heading anchor not found"
s = s.replace(old_head, new_head, 1)

# ---- 3. load them with the chapters --------------------------------------
old_load = '''  if(S.current) loadChapters(S.current).catch(function(){});'''
new_load = '''  if(S.current){
    loadChapters(S.current).catch(function(){});
    loadSeasons(S.current).catch(function(){});
  }'''
assert old_load in s, "load anchor not found"
s = s.replace(old_load, new_load, 1)

# ---- 4. the panel itself, and a season-aware start -----------------------
js = '''
<script>
// ---------- production seasons ----------
// A long book is made a season at a time. This shows what each season
// took and what it left, and starts a new one over the picked chapters.
async function loadSeasons(slug){
  const r = await getJSON("/api/seasons?project="+encodeURIComponent(slug));
  const box = document.getElementById("seasonList");
  if(!box) return;
  if(!r || !r.ok){
    box.innerHTML = '<div class="muted">读不到季记录</div>';
    return;
  }
  window.__seasons = r.seasons || [];
  window.__nextSeason = r.current || 1;
  const card = document.getElementById("work-seasons");
  if(card) card.style.display = "";
  const hint = document.getElementById("seasonHint");
  if(hint) hint.textContent = "已完成 " + (r.chapters_done||0) + " / " +
      (r.chapters_total||0) + " 章 · 下一季从第 " + (r.next_chapter||1) + " 章起";
  const rows = (window.__seasons||[]).map(se=>{
    const span = (se.chapters&&se.chapters.length)
      ? ("第" + Math.min.apply(null,se.chapters) + "~" +
         Math.max.apply(null,se.chapters) + "章") : "（旧数据）";
    const st = se.status==="done" ? "完成" : (se.status==="failed" ? "失败" : "进行中");
    const tone = se.status==="done" ? "var(--go2)"
               : (se.status==="failed" ? "var(--danger)" : "var(--warn)");
    return '<div style="display:flex;gap:8px;align-items:center;padding:4px 0;' +
      'border-bottom:1px solid var(--line)">' +
      '<b>第' + se.index + '季</b>' +
      '<span class="mini" style="color:' + tone + '">' + st + '</span>' +
      '<span class="mini muted">' + span + '</span>' +
      '<span class="mini muted">' + (se.episodes||0) + ' 集</span>' +
      (se.synopsis ? '<span class="mini muted" style="flex:1;overflow:hidden;' +
        'text-overflow:ellipsis;white-space:nowrap">' + esc(se.synopsis) + '</span>'
        : '<span style="flex:1"></span>') +
      '</div>';
  }).join("");
  box.innerHTML = rows || '<div class="muted">还没有季，选中章节后开始第一季</div>';
}

// Start a season over whatever is picked. One season is one whole run of
// the pipeline - analysis through the finished film - not three stages of
// it, because a batch of chapters is a batch of episodes and half of one
// is not an episode anyone can watch.
async function startSeason(){
  const slug = S.current;
  if(!slug){ toast("先选一个项目","err"); return; }
  const chosen = Array.from(_chapChosenSet());
  if(!chosen.length){ toast("先勾选要做的章节","err"); return; }
  const season = window.__nextSeason || 1;
  const r = await postJSON("/api/chapters/choose",{project:slug,chosen:chosen});
  if(!r || !r.ok){ toast("保存选章失败："+esc((r&&r.error)||"未知错误"),"err"); return; }
  const run = await postJSON("/api/run",{project:slug,season:season,
                                     stages:STAGES.slice()});
  if(!run || !run.ok){ toast("启动失败："+esc((run&&run.error)||"未知错误"),"err"); return; }
  toast("第" + season + "季开始，共 " + chosen.length + " 章","",2400);
  pollJob(run.job, (res,j)=>{
    if(!j) return;
    if(j.status==="error") return;
    toast("第" + season + "季完成","",3000);
    selectProject(slug,true).then(()=>renderWorkbench());
  });
}
</script>
'''
i = s.find("</body>")
assert i > 0, "no </body>"
s = s[:i] + js + s[i:]

# ---- 5. the start button runs a season, not three stages -----------------
old_btn = '               onclick="chooseChapters()">'
new_btn = '               onclick="startSeason()">'
assert old_btn in s, "start button anchor not found"
# the label too: three stages of the pipeline is not what this does now
end = s.index("</button>", s.index(old_btn))
s = s[:s.index(old_btn)] + new_btn + "开始新的一季</button>" + s[end + len("</button>"):]

p.write_text(s, encoding="utf-8")
print("index.html: seasons panel + one-click whole-season run")
