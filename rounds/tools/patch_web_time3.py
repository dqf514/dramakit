"""Show the film's time on the console page."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8")

old = """      ${ep.video?`<a class="mini" href="${ep.video}" target="_blank" style="margin-left:6px">▶ 成片</a>`:""}"""
new = """      ${ep.video?`<a class="mini" href="${ep.video}" target="_blank" style="margin-left:6px">▶ 成片</a>`:""}
      ${ep.video_mtime?`<span class="muted" style="font-size:11px;margin-left:6px">${ep.video_seconds?ep.video_seconds+"s · ":""}最后生成 ${ago(ep.video_mtime)}（${whenStr(ep.video_mtime)}）</span>`:""}"""
assert old in s, "成片锚点没找到"
s = s.replace(old, new, 1)

old = """      ${ep.video?'<a class="mini" href="'+ep.video+'" target="_blank">成片 ↗</a>':""}"""
new = """      ${ep.video?'<a class="mini" href="'+ep.video+'" target="_blank">成片 ↗</a>':""}
      ${ep.video_mtime?`<span class="muted" style="font-size:10.5px">${ago(ep.video_mtime)}</span>`:""}"""
assert old in s, "成片2锚点没找到"
s = s.replace(old, new, 1)

old = """const STAGE_HINT="""
new = """function ago(ts){if(!ts)return "";const s=(Date.now()/1000-ts);if(s<60)return "刚刚";if(s<3600)return Math.floor(s/60)+" 分钟前";if(s<86400)return Math.floor(s/3600)+" 小时前";if(s<86400*7)return Math.floor(s/86400)+" 天前";return new Date(ts*1000).toLocaleDateString();}
function whenStr(ts){if(!ts)return "";const d=new Date(ts*1000);const p=n=>String(n).padStart(2,"0");return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;}
const STAGE_HINT="""
assert old in s, "STAGE_HINT 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("index.html 已改")
