"""Show when the episode was made - take two (the right anchor)."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

old = """            def _sv(s):
                return s.value if hasattr(s, "value") else str(s or "")"""
new = """            def _sv(s):
                return s.value if hasattr(s, "value") else str(s or "")

            def _mtime(rel: str) -> float:
                \"\"\"When the file was written (0 when there is none).\"\"\"
                if not rel:
                    return 0.0
                try:
                    f = store.abs(rel)
                    return round(f.stat().st_mtime, 1) if f.exists() else 0.0
                except Exception:  # noqa: BLE001
                    return 0.0

            def _duration(rel: str) -> float:
                \"\"\"How long the finished film is.\"\"\"
                if not rel:
                    return 0.0
                try:
                    from ..media.ffmpeg import probe_duration
                    return round(float(probe_duration(store.abs(rel))), 2)
                except Exception:  # noqa: BLE001
                    return 0.0"""
assert old in s, "_sv 锚点没找到"
s = s.replace(old, new, 1)

old = """                episodes.append({
                    "id": ep.id, "index": ep.index, "title": ep.title,"""
new = """                episodes.append({
                    "id": ep.id, "index": ep.index, "title": ep.title,
                    "video_mtime": _mtime(ep.video_path),
                    "video_seconds": _duration(ep.video_path),"""
assert old in s, "episodes 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("server.py 已改")
