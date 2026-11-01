"""Stop a run from the page, and let a stopped stage say so.

The backend can be asked to stop now, but nothing on the page could ask:
the panel that shows a running stage is where the button belongs, since
that is where the user finds out the plan was wrong. And a stage that was
stopped had no badge of its own, so it would have shown as pending - as
if the work had not been attempted, rather than as work someone refused
to continue.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8")

if "stopRun" in s:
    print("index.html: 停止按钮已存在，跳过")
    raise SystemExit(0)

# --------------------------------------------- 1. a badge for stopped ----
old_badge = '''function badge(st){
  const m={done:["done","完成"],running:["run","进行"],failed:["fail","失败"],pending:["","待办"],skipped:["","跳过"]};
  const x=m[st]||["",st||""];
  return `<span class="badge ${x[0]}">${esc(x[1])}</span>`;
}'''
new_badge = '''function badge(st){
  const m={done:["done","完成"],running:["run","进行"],failed:["fail","失败"],
           pending:["","待办"],skipped:["","跳过"],
           // a refusal, not a fault: the work was not bad, it was stopped
           interrupted:["fail","已中断"]};
  const x=m[st]||["",st||""];
  return `<span class="badge ${x[0]}">${esc(x[1])}</span>`;
}'''
assert old_badge in s, "badge 锚点没找到"
s = s.replace(old_badge, new_badge, 1)

# ------------------------------------- 2. the stage strip marks it too ----
old_mark = '''    const mark=v==="done"?"●":v==="running"?"◐":"○";
    const col=v==="done"?"var(--go2)":v==="running"?"var(--confirm)":"var(--fg3)";'''
new_mark = '''    const mark=v==="done"?"●":v==="running"?"◐":v==="interrupted"?"◑":"○";
    const col=v==="done"?"var(--go2)":v==="running"?"var(--confirm)"
             :v==="interrupted"?"var(--warn)":"var(--fg3)";'''
assert old_mark in s, "阶段条带锚点没找到"
s = s.replace(old_mark, new_mark, 1)

# ------------------------------------------- 3. the button on the panel --
old_panel = '''      ${item}
      <span style="flex:1"></span>
      ${ms==null?"":`<span class="mini muted">已运行 ${fmtDur(ms)}</span>`}
    </div>'''
new_panel = '''      ${item}
      <span style="flex:1"></span>
      ${ms==null?"":`<span class="mini muted">已运行 ${fmtDur(ms)}</span>`}
      <button class="btn ghost" id="stopRunBtn" onclick="stopRun()"
              title="在下一集/下一阶段停下，已完成的保留">停止</button>
    </div>'''
assert old_panel in s, "进度面板锚点没找到"
s = s.replace(old_panel, new_panel, 1)

# ------------------------------------------------- 4. the asking itself --
js = '''
<script>
// ---------- stop a run ----------
// The pipeline asks whether to continue before each stage and before each
// episode, so this takes effect at the next item rather than at the end of
// the batch - which is the only reason to have a button at all.
async function stopRun(){
  const btn=document.getElementById("stopRunBtn");
  if(btn){ btn.disabled=true; btn.textContent="正在停…"; }
  const r=await postJSON("/api/jobs/stop",{});
  if(!r||!r.ok){
    if(btn){ btn.disabled=false; btn.textContent="停止"; }
    toast((r&&r.error)||"停不下来","err",4000);
    return;
  }
  toast("已请求停止，将在当前这一集结束后停下","",4000);
  // the panel keeps polling; the stage will show as interrupted when the
  // run has actually let go
  setTimeout(()=>{ updateProgressPanel(); }, 2500);
}
</script>
'''
i = s.find("</body>")
assert i > 0, "找不到 </body>"
s = s[:i] + js + s[i:]

p.write_text(s, encoding="utf-8")
print("index.html: 进度面板有停止按钮，中断有专属标记")
