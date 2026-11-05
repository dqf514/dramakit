"""The workbench, in the order the work is done in.

Before: the settings and the chapters were in a column on the right,
the steps were in the middle, and the skills were below them - so the
order on the page was not the order of the work.  And the steps that
were picked were marked with a line of blue, which is easy to miss
among five cards.

Now: the frame, the resolution and the look are chosen first, then the
chapters, then the steps, then the skills, then the episodes.  The look
brings its own skills with it - a story set in the Republican era is
written with different craft than a sweet romance - and the person can
take anything off that list and add anything back.
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


# 1. the page: the settings and the chapters come first, side by side
old = '''        <div class="card">
          <h3>制作步骤 <span class="muted" style="font-weight:400;font-size:12px">点一下选中或取消 · 已完成 ${doneSteps}/${STEPS.length}</span></h3>'''
new = '''        <div class="wb-setup">
          ${lookPanelHtml(d)}
          ${chapterHtml}
        </div>

        <div class="card">
          <h3>制作步骤 <span class="muted" style="font-weight:400;font-size:12px">点一下选中或取消 · 已完成 ${doneSteps}/${STEPS.length}</span></h3>'''
assert old in text, "没找到制作步骤"
text = text.replace(old, new, 1)

# the sidebar goes: both of its cards are in the main column now
old = '''      <aside class="wb-side">
        ${lookPanelHtml(d)}
        ${chapterHtml}
      </aside>
    </div>
    `;'''
new = '''    </div>
    `;'''
assert old in text, "没找到侧栏"
text = text.replace(old, new, 1)

# 2. the grid: one column, and the setup row is two
sub(r'\.wb-grid\{display:grid;grid-template-columns:minmax\(0,1fr\) 372px;gap:12px;align-items:start\}',
    '.wb-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;align-items:start}\n'
    '  .wb-setup{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;\n'
    '    align-items:start;margin-bottom:12px}\n'
    '  .wb-setup > .card{margin-bottom:0}',
    "wb-grid")

# 3. a picked step says so, loudly
sub(r'\.step\.on\{outline:2px solid var\(--confirm\);outline-offset:1px\}',
    '.step.on{border-color:var(--confirm);outline:2px solid var(--confirm);\n'
    '    outline-offset:1px;background:color-mix(in srgb,var(--confirm) 14%,var(--bg2));\n'
    '    box-shadow:0 2px 10px rgba(0,0,0,.18)}\n'
    '  .step.on .sn{color:var(--confirm)}\n'
    '  .step.on .st{color:var(--fg)}\n'
    '  .step .tick{margin-left:auto;font-size:11.5px;font-weight:700;color:var(--confirm);\n'
    '    border:1px solid var(--confirm);border-radius:9px;padding:0 6px;line-height:1.5}',
    "step.on")

# 4. the badge in the card
sub(r'<span class="st"><span class="dot \$\{dot\}"></span>\$\{sp\.zh\}</span>',
    '<span class="st"><span class="dot ${dot}"></span>${sp.zh}'
    '${stepSelected(sp)?\'<span class="tick">已选</span>\':""}</span>',
    "the step badge")

# 5. the look brings its skills with it
old = '''  const st=$("#lookStyle");
  if(st) st.onchange=()=>lookDraftSet({style:st.value});'''
new = '''  const st=$("#lookStyle");
  if(st) st.onchange=()=>{
    lookDraftSet({style:st.value});
    applyStyleSkills(st.value);
  };'''
assert old in text, "没找到风格选择"
text = text.replace(old, new, 1)

# and the function that does it
old = '''// ---------- the skills, listed by step ----------'''
new = '''// The look decides what the writing has to be good at: a story set in
// the Republican era is written with different craft than a sweet
// romance.  Choosing a look brings its skills with it - and the person
// can take anything off the list and add anything back, and the change
// is saved as they make it.
async function applyStyleSkills(styleId){
  if(!styleId||!SK||!SK.by_style) return;
  const got=SK.by_style[styleId];
  if(!got||!got.skills) return;
  const names=(SK.skills||[]).map(x=>x.name);
  const clean={};
  for(const stage of ["analyze","script","storyboard","promptgen"]){
    const want=(got.skills[stage]||[]).filter(n=>names.indexOf(n)>=0);
    if(want.length) clean[stage]=want;
  }
  const r=await postJSON("/api/skills/save",{project:S.current,selection:clean});
  if(!r||!r.ok){ toast("技能保存失败","err"); return; }
  SK.selection=r.selection||SK.selection;
  SK.costs=r.costs||SK.costs;
  SK.recommended=false;
  renderFlow();
  toast("已按「"+esc(got.name)+"」换了一套技能，可以再改","ok",3200);
}

// ---------- the skills, listed by step ----------'''
assert old in text, "没找到技能那节"
text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8")
print("版面改好了")
