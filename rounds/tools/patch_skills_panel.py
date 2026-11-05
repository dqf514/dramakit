"""The skills panel: only what has to be decided, and no scrolling.

There were five columns, one per step, and three of them said "this
step injects no skills" - the space of three empty columns.  The
column that mattered was one step, and inside it the three stages
that write with skills were stacked, so the list of theory skills
needed a scrollbar to be seen at all.

Now: one column for every stage that actually takes skills, the
checkboxes flow across in two sub-columns, and nothing scrolls.
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


# 1. the panel: a column for every stage that takes skills
old_start = "function skillsPanelHtml(){"
i = text.index(old_start)
j = text.index("\n}\n", i) + 3
new_panel = '''function skillsPanelHtml(){
  if(!SK) return `<div class="card"><b>技能</b><span class="muted" style="font-size:12px">读取中…</span></div>`;
  const sel=SK.selection||{}, costs=SK.costs||{};
  // A column for every stage that takes skills, and none for the steps
  // that inject nothing: three empty columns were space taken for
  // nothing.
  const stepOf={analyze:"准备",script:"剧本",storyboard:"剧本",promptgen:"剧本"};
  const cols=Object.keys(SK_STAGE_ZH).map(st=>{
    const names=sel[st]||[];
    const opts=skillsForStage(st).map(x=>`<label class="skck"
        title="${attr(x.description||"")}"><input type="checkbox" data-skstage="${esc(st)}"
        data-sk="${esc(x.name)}" ${names.indexOf(x.name)>=0?"checked":""}><span>${esc(skLabel(x))}</span></label>`).join("");
    return `<div class="skcol">
      <div class="skt">${esc(SK_STAGE_ZH[st])}
        <span class="skstep">${esc(stepOf[st]||"")}</span>
        <span class="muted" style="margin-left:auto">${names.length} 个 · ${fmtChars(costs[st]||0)}</span>
      </div>
      <div class="skopts">${opts}</div></div>`;
  }).join("");
  const rec=SK.recommended?" · 按这本书推荐的":"";
  return `<div class="card">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <b>技能</b>
      <span class="muted" style="font-size:12px">勾上就存到本项目，下次跑流水线生效${esc(rec)}</span>
    </div>
    <div class="skgrid">${cols}</div>
  </div>`;
}
'''
text = text[:i] + new_panel + text[j:]

# 2. the columns: as many as the stages need, and the checkboxes flow
sub(r'\.skgrid\{display:grid;grid-template-columns:repeat\(5,minmax\(0,1fr\)\);gap:8px;margin-top:8px\}',
    '.skgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));'
    'gap:8px;margin-top:8px}',
    "skgrid")
sub(r'\.skopts\{max-height:190px;overflow:auto;display:flex;flex-direction:column;gap:2px;padding-right:2px\}',
    '.skopts{columns:2;column-gap:10px;padding-right:2px}\n'
    '  .skopts .skck{break-inside:avoid}',
    "skopts")
sub(r'(\.skcol \.skt\{font-weight:650;font-size:12\.5px;margin-bottom:6px\})',
    r'\1  .skcol .skt{display:flex;align-items:center;gap:6px}\n'
    '  .skcol .skstep{font-weight:400;font-size:11px;color:var(--fg3);\n'
    '    border:1px solid var(--line);border-radius:4px;padding:0 4px}',
    "skt")

# 3. the note about where the selection came from
sub(r'(if\(path=="/api/skills"\):)',
    r'\1', "api skills", count=0) if False else None

PATH.write_text(text, encoding="utf-8")
print("技能面板改好了")
