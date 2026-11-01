"""The skills become a page: what each stage writes with, and what it costs.

The rules each stage sends lived in a YAML file, so finding out meant
reading code and changing it meant editing configuration and restarting -
and a run that is going cannot be restarted. The page lists what exists,
what each stage is using, and what that costs in characters, since a
skill is sent with every call and the prompt stage was measured at ten
thousand characters per shot because two of them were always on.

A skill can be given to any stage, because the folders do not always
agree with the work: a theory skill about character conflict earns its
place in the screenplay stage and sometimes in the storyboard one. And
the model can be asked, reading the project's genre, synopsis and cast
against each skill's own description, which turns thirty-seven choices
into one question.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8")

if "page-skills" in s:
    print("index.html: 技能页已存在，跳过")
    raise SystemExit(0)

# ------------------------------------------------------------- CSS ------
css = """
<style>
/* the skills page: what each stage writes with, and what it costs */
.sk-row{display:flex;gap:10px;align-items:flex-start;padding:9px 0;
  border-bottom:1px solid var(--line)}
.sk-row:last-child{border-bottom:0}
.sk-name{font-weight:650;font-size:12.5px;white-space:nowrap}
.sk-size{color:var(--fg3);font-size:10.5px;white-space:nowrap;
  min-width:78px;text-align:right}
.sk-desc{color:var(--fg2);font-size:11.5px;line-height:1.55;flex:1;min-width:0}
.sk-pick{border:1px solid var(--line);background:var(--bg3);color:var(--fg2);
  border-radius:5px;padding:2px 8px;font-size:11px;cursor:pointer;
  white-space:nowrap;font-family:inherit}
.sk-pick:hover{border-color:var(--confirm);color:var(--confirm)}
.sk-pick.on{background:var(--confirm);border-color:var(--confirm);color:#fff}
.sk-cost{font-variant-numeric:tabular-nums}
</style>
"""
i = s.find("</style>")
s = s[:i] + css + s[i:]

# ------------------------------------------------- the rail button -------
old_btn = '''    <button class="railbtn" data-page="settings" title="设置">'''
new_btn = '''    <button class="railbtn" data-page="skills" title="技能">
      <svg viewBox="0 0 24 24"><path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 1-2-2V5z"/><path d="M9 3v18"/></svg>
      <span>技能</span>
    </button>
    <button class="railbtn" data-page="settings" title="设置">'''
assert old_btn in s, "设置按钮锚点没找到"
s = s.replace(old_btn, new_btn, 1)

# ------------------------------------------------ the page section ------
old_sec = '''<section id="page-assets" class="page" style="display:none"></section>'''
new_sec = old_sec + '''
<section id="page-skills" class="page" style="display:none"></section>'''
assert old_sec in s, "page-assets 锚点没找到"
s = s.replace(old_sec, new_sec, 1)

# -------------------------------------------------- the switch branch ----
old_sw = '''  if(name==="assets"){ renderAssetsPage(); loadAssets(); }'''
new_sw = '''  if(name==="assets"){ renderAssetsPage(); loadAssets(); }
  if(name==="skills") renderSkills();'''
assert old_sw in s, "switchPage 锚点没找到"
s = s.replace(old_sw, new_sw, 1)

# ------------------------------------------------ the page itself --------
js = '''
<style>
</style>
<script>
// ---------- the skills: what each stage writes with ----------
// The stages send their skills with every model call, so a list that
// looks harmless is a multiplier on the whole batch - the prompt stage
// was measured at ten thousand characters per shot because two skills
// were always on. What one costs is shown next to it.
const SK_STAGES=[["analyze","分析"],["script","编剧"],
                 ["storyboard","分镜"],["promptgen","提示词"]];
let SK=null;   // {skills, selection, costs}

function fmtChars(n){ return n>=10000 ? (n/10000).toFixed(1)+"万字" : (n||0)+"字"; }

async function loadSkills(){
  const slug=S.current;
  const q=slug?("?project="+encodeURIComponent(slug)):"";
  const r=await getJSON("/api/skills"+q);
  if(!r||!r.ok){ toast("读不到技能目录","err"); return; }
  SK=r;
  renderSkills();
}

function renderSkills(){
  const box=$("#page-skills");
  if(!SK){ box.innerHTML='<div class="empty">读取中…</div>'; loadSkills(); return; }
  const sel=SK.selection||{}, costs=SK.costs||{};
  const byName={}; (SK.skills||[]).forEach(x=>byName[x.name]=x);

  // what each stage is using, and what that costs per call
  const stageHtml=SK_STAGES.map(([k,zh])=>{
    const names=sel[k]||[];
    const chips=names.length
      ? names.map(n=>`<span class="chip on" title="${esc((byName[n]||{}).description||"")}"
            onclick="skillPick('${esc(k)}','${esc(n)}')">${esc((byName[n]||{}).title||n)} ×</span>`).join("")
      : '<span class="muted">不使用技能（用内置规矩）</span>';
    return `<div class="card" style="margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:8px">
        <b>${esc(zh)}</b>
        <span class="mini muted">每次调用注入</span>
        <b class="sk-cost" style="color:${(costs[k]||0)>6000?"var(--danger2)":"var(--fg2)"}">${fmtChars(costs[k]||0)}</b>
        <span style="flex:1"></span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:7px">${chips}</div>
    </div>`;
  }).join("");

  // every skill there is, grouped by family
  const fams={};
  (SK.skills||[]).forEach(x=>{ (fams[x.family_zh]=fams[x.family_zh]||[]).push(x); });
  const rows=Object.keys(fams).map(fam=>{
    const list=fams[fam];
    const total=list.reduce((a,x)=>a+x.chars,0);
    return `<h3 class="page" style="font-size:13px;margin:16px 0 6px">${esc(fam)}
        <span class="muted" style="font-weight:400;font-size:11px">${list.length} 个 · ${fmtChars(total)}</span></h3>
      <div class="card" style="padding:4px 14px">${list.map(x=>skillRow(x,sel)).join("")}</div>`;
  }).join("");

  box.innerHTML=`
    <h1 class="page">技能</h1>
    <div class="sub">每个阶段写作用的规矩文档。技能随每次模型调用发送——越多越准，也越慢。</div>
    <div class="card" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <span class="mini muted">当前项目</span>
      <b>${esc((S.detail&&S.detail.meta&&(S.detail.meta.title||S.detail.meta.name))||S.current||"（未选项目）")}</b>
      <span style="flex:1"></span>
      <button class="btn ai" id="skReco" onclick="recommendSkills()">✦ 让 AI 按本项目挑</button>
      <button class="btn go" onclick="saveSkills()">保存到本项目</button>
    </div>
    <div id="skRecoBox"></div>
    <h2 class="page" style="font-size:14px;margin:14px 0 8px">各阶段在用</h2>
    ${stageHtml}
    <h2 class="page" style="font-size:14px;margin:16px 0 8px">全部技能
      <span class="muted" style="font-weight:400;font-size:11px">点右边的阶段名加入或移出</span></h2>
    ${rows}`;
}

function skillRow(x, sel){
  const picks=SK_STAGES.map(([k,zh])=>{
    const on=(sel[k]||[]).indexOf(x.name)>=0;
    return `<button class="sk-pick ${on?"on":""}"
      onclick="skillPick('${esc(k)}','${esc(x.name)}')">${esc(zh)}</button>`;
  }).join("");
  const desc=(x.description||"").replace(/\\s+/g," ").slice(0,150);
  return `<div class="sk-row">
    <div style="min-width:0">
      <span class="sk-name">${esc(x.title||x.name)}</span>
      <span class="sk-size">${fmtChars(x.chars)}</span>
      <div class="sk-desc" title="${esc(x.description||"")}">${esc(desc)}${(x.description||"").length>150?"…":""}</div>
      ${x.refs?`<div class="mini muted" style="margin-top:3px">另有 ${x.refs} 个深参考（${fmtChars(x.ref_chars)}，当前不注入）</div>`:""}
    </div>
    <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end">${picks}</div>
  </div>`;
}

function skillPick(stage,name){
  if(!SK) return;
  const list=SK.selection[stage]=SK.selection[stage]||[];
  const i=list.indexOf(name);
  if(i>=0) list.splice(i,1); else list.push(name);
  // the cost moves with the choice, so the multiplier is never a surprise
  SK.costs=SK.costs||{};
  SK.costs[stage]=(SK.costs[stage]||0)+(i>=0?-(SK.skills.find(x=>x.name===name)||{chars:0}).chars
                                             :(SK.skills.find(x=>x.name===name)||{chars:0}).chars);
  if(SK.costs[stage]<0) SK.costs[stage]=0;
  renderSkills();
}

async function saveSkills(){
  if(!S.current){ toast("先选一个项目","err"); return; }
  const r=await postJSON("/api/skills/save",{project:S.current,selection:SK.selection});
  if(!r||!r.ok){ toast("保存失败："+esc((r&&r.error)||"未知错误"),"err"); return; }
  SK.costs=r.costs||SK.costs;
  toast("已保存。下次跑流水线生效（正在跑的不受影响）","ok",4000);
  renderSkills();
}

async function recommendSkills(){
  if(!S.current){ toast("先选一个项目","err"); return; }
  const btn=document.getElementById("skReco");
  if(btn){ btn.disabled=true; btn.textContent="正在读项目…"; }
  const r=await postJSON("/api/skills/recommend",{project:S.current});
  if(btn){ btn.disabled=false; btn.textContent="✦ 让 AI 按本项目挑"; }
  if(!r||!r.ok){ toast("推荐失败："+esc((r&&r.error)||"未知错误"),"err",5000); return; }
  SK.selection=r.selection||{};
  SK.costs=r.costs||{};
  const box=document.getElementById("skRecoBox");
  if(box&&r.reasons){
    const rows=Object.keys(r.reasons).map(k=>
      `<div class="sk-row"><span class="sk-name">${esc(k)}</span>
       <div class="sk-desc">${esc(r.reasons[k])}</div></div>`).join("");
    box.innerHTML=`<div class="card" style="margin-bottom:8px">
      <b>AI 的理由</b><div style="margin-top:6px">${rows}</div>
      <div class="mini muted" style="margin-top:8px">还没保存——确认后点「保存到本项目」。</div>
    </div>`;
  }
  renderSkills();
}
</script>
'''
j = s.find("</body>")
s = s[:j] + js + s[j:]

p.write_text(s, encoding="utf-8")
print("index.html: 技能页（按阶段选 + 成本显示 + AI 推荐）")
