"""Draw the run's progress in the console.

What the person watching wants to see is not a bar that moves but what
is actually happening: how many requests are in flight, which stage
each lane is on, how many are done and how many failed.  So the panel
grows a table of the stages and a line for the lanes.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")

# 1. keep what the api says about the whole run
old_poll = '''      S.progress=pr.progress||{};
      if(pr.project&&S.detail){'''
new_poll = '''      S.progress=pr.progress||{};
      S.runStats={stages:pr.stages||{},lanes:pr.lanes||{},inflight:pr.inflight||0,
                  started:pr.started||0,done:pr.done||0,failed:pr.failed||0,
                  total:pr.total||0,now:pr.now||0};
      if(pr.project&&S.detail){'''
assert old_poll in text, "找不到轮询"
text = text.replace(old_poll, new_poll, 1)

# 2. the overview: a table of the stages and the lanes
helper = '''
// how wide the work is, and how it is going - a table of the stages and
// a line for each lane.  A bar that moves says nothing about how many
// requests are in flight or how many of them are failing.
const LANE_ZH={"写作":"写作","旁路":"旁路","绘制":"绘制"};
function progressOverviewHtml(){
  const st=S.runStats||{};
  const stages=st.stages||{};
  const names=Object.keys(stages);
  if(!names.length) return "";
  const order=["script","storyboard","promptgen","voice","music","visual","compose","qc"];
  names.sort((a,b)=>{
    const ia=order.indexOf(a), ib=order.indexOf(b);
    return (ia<0?99:ia)-(ib<0?99:ib);
  });
  const rows=names.map(k=>{
    const v=stages[k]||{};
    const zh=STAGE_ZH[k]||k;
    const run=+v.running||0, done=+v.done||0, fail=+v.failed||0;
    const started=+v.started||0, total=+v.total||0, conc=+v.concurrency||0;
    const since=+v.since||0, now=+st.now||0;
    const secs=since?Math.max(0,Math.round((now-since)/1000)):0;
    const busy=run>0;
    const mark=busy?"<span style='color:var(--confirm)'>◉</span>"
            :(total&&done>=total)?"<span style='color:var(--go2)'>●</span>"
            :(fail?"<span style='color:var(--danger2)'>▲</span>":"<span class='muted'>○</span>");
    return `<tr>
      <td style="white-space:nowrap">${mark} ${esc(zh)}</td>
      <td style="text-align:right">${started}</td>
      <td style="text-align:right;color:${busy?"var(--confirm)":"var(--fg3)"}">${run}</td>
      <td style="text-align:right;color:var(--go2)">${done}</td>
      <td style="text-align:right;color:${fail?"var(--danger2)":"var(--fg3)"}">${fail}</td>
      <td style="text-align:right" class="muted">${total||"—"}</td>
      <td style="text-align:right" class="muted">${conc||"—"}</td>
      <td style="text-align:right" class="muted">${secs?fmtDur(secs*1000):"—"}</td>
    </tr>`;
  }).join("");
  const lanes=st.lanes||{};
  const laneBits=Object.keys(lanes).map(l=>{
    const zh=LANE_ZH[l]||l;
    const s=STAGE_ZH[lanes[l]]||lanes[l];
    return `<span class="mini" style="margin-right:10px"><span style="color:var(--confirm)">◉</span> ${esc(zh)}·${esc(s)}</span>`;
  }).join("");
  const inflight=+st.inflight||0;
  const head=`<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px">
    <span class="mini"><b style="color:var(--confirm);font-size:13px">${inflight}</b> 路请求在飞</span>
    <span class="mini muted">已发起 ${+st.started||0} · 完成 ${+st.done||0}${+st.failed?` · 失败 ${+st.failed}`:""}</span>
    <span style="flex:1"></span>
    ${laneBits}
  </div>`;
  return head+`<table style="width:100%;font-size:12px;border-collapse:collapse">
    <tr style="color:var(--fg3);text-align:left">
      <th style="font-weight:500;padding:2px 8px 2px 0">阶段</th>
      <th style="font-weight:500;text-align:right;padding:2px 4px">已发起</th>
      <th style="font-weight:500;text-align:right;padding:2px 4px">在跑</th>
      <th style="font-weight:500;text-align:right;padding:2px 4px">完成</th>
      <th style="font-weight:500;text-align:right;padding:2px 4px">失败</th>
      <th style="font-weight:500;text-align:right;padding:2px 4px">共计</th>
      <th style="font-weight:500;text-align:right;padding:2px 4px">并发</th>
      <th style="font-weight:500;text-align:right;padding:2px 4px">用时</th>
    </tr>
    ${rows}
  </table>`;
}
'''

marker = "// the panel: which stage, what it is for, and the pipeline lit to here"
assert marker in text, "找不到插入点"
text = text.replace(marker, helper + marker, 1)

# 3. the panel shows the overview, and shows it even between stages
old_panel = '''function workProgressHtml(){
  const st=runningStageName();
  if(!st) return "";
  const zh=STAGE_ZH[st]||st;'''
new_panel = '''function workProgressHtml(){
  const overview=progressOverviewHtml();
  const st=runningStageName();
  if(!st) return overview?`<div class="card" style="margin-bottom:10px">${overview}</div>`:"";
  const zh=STAGE_ZH[st]||st;'''
assert old_panel in text, "找不到面板"
text = text.replace(old_panel, new_panel, 1)

old_tail = '''    ${hint?`<div class="muted" style="font-size:12.5px;margin-top:6px">${esc(hint)}</div>`:""}
    ${bar}
    <div class="prog-strip">${strip}</div>
  </div>`;
}'''
new_tail = '''    ${hint?`<div class="muted" style="font-size:12.5px;margin-top:6px">${esc(hint)}</div>`:""}
    ${bar}
    <div class="prog-strip">${strip}</div>
    ${overview?`<div style="margin-top:9px;padding-top:8px;border-top:1px solid var(--line)">${overview}</div>`:""}
  </div>`;
}'''
assert old_tail in text, "找不到面板尾"
text = text.replace(old_tail, new_tail, 1)

PATH.write_text(text, encoding="utf-8")
print("前端改好了")
