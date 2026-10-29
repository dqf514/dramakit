"""Show when the episode was made.

The console listed the episode and its video, but not when the file was
written - so there was no way to tell whether the film on screen was the
one from this morning or from the last run.
"""
from pathlib import Path

# 1) the API: the times of the episode's files
p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

old = """                episodes.append({
                    "id": ep.id, "index": ep.index, "title": ep.title,"""
new = """                episodes.append({
                    "id": ep.id, "index": ep.index, "title": ep.title,
                    "video_mtime": _mtime(ep.video_path),
                    "video_seconds": _duration(ep.video_path),
                    "updated_at": _mtime(""),"""
assert old in s, "episodes 锚点没找到"
s = s.replace(old, new, 1)

# the helpers
old = """def _sv(v) -> str:"""
new = '''def _mtime(rel: str) -> float:
    """When the file was written (0 when there is none)."""
    if not rel:
        return 0.0
    try:
        p = Path(store_abs(rel))
        return round(p.stat().st_mtime, 1) if p.exists() else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def _duration(rel: str) -> float:
    """How long the finished film is."""
    if not rel:
        return 0.0
    try:
        from ..media.ffmpeg import probe_duration
        return round(float(probe_duration(store_abs(rel))), 2)
    except Exception:  # noqa: BLE001
        return 0.0


def _sv(v) -> str:'''
assert old in s, "_sv 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("server.py 已改（接口带成片时间）")

# 2) the page: show it next to the film
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

# the helpers for the page
old = """const STAGE_HINT="""
new = """function ago(ts){if(!ts)return "";const s=(Date.now()/1000-ts);if(s<60)return "刚刚";if(s<3600)return Math.floor(s/60)+" 分钟前";if(s<86400)return Math.floor(s/3600)+" 小时前";if(s<86400*7)return Math.floor(s/86400)+" 天前";return new Date(ts*1000).toLocaleDateString();}
function whenStr(ts){if(!ts)return "";const d=new Date(ts*1000);const p=n=>String(n).padStart(2,"0");return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;}
const STAGE_HINT="""
assert old in s, "STAGE_HINT 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("index.html 已改（显示成片时间）")
