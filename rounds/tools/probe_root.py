"""Whether the pictures that appeared are real, and where the path went.

Five files landed in the new character's folder while every render was
reported as failing, which cannot both be true: either the pictures are
something else - stale, empty, copied - or the failure was about a
different thing than it said.

So the files are opened and identified rather than counted, and the
workflow path is resolved the way each context resolves it, to see which
root the one in this script was built with.
"""
import json
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
cdir = proj / "characters" / "素素"

out.append(f"=== {cdir} ===")
if not cdir.exists():
    out.append("  目录不存在")
else:
    for f in sorted(cdir.iterdir()):
        st = f.stat()
        head = f.read_bytes()[:16]
        kind = ("PNG" if head[:8] == b"\x89PNG\r\n\x1a\n"
                else "JPEG" if head[:2] == b"\xff\xd8"
                else "MP3" if head[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3")
                else f"未知 {head[:8]!r}")
        out.append(f"  {f.name:22} {st.st_size:>9,} B  "
                   f"{time.strftime('%m-%d %H:%M:%S', time.localtime(st.st_mtime))}"
                   f"  {kind}")

# --- what the pipeline's own images look like, for comparison -----------
out.append("")
out.append("=== 别的角色的参考图（对照）===")
for d in sorted((proj / "characters").iterdir())[:3]:
    if not d.is_dir() or d.name == "素素":
        continue
    for f in sorted(d.iterdir())[:3]:
        head = f.read_bytes()[:8]
        kind = "PNG" if head == b"\x89PNG\r\n\x1a\n" else (
            "JPEG" if head[:2] == b"\xff\xd8" else "其他")
        out.append(f"  {d.name}/{f.name:20} {f.stat().st_size:>9,} B  {kind}")

# --- how each context resolves the workflow path -----------------------
out.append("")
out.append("=== root 是怎么来的 ===")
from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402

cfg = Config.load(Config.discover())
store = ProjectStore.open(proj)
ctx = Context(cfg, store)
out.append(f"  Context.providers.root = {ctx.providers.root}")
out.append(f"  cfg 根路径候选:")
out.append(f"    ComfyUIConfig 无 root 字段，工作流由 client.root 解析")

# the client the pool builds for the local node
vis = ctx.providers.visual
out.append(f"  visual provider = {type(vis).__name__}")
for n in (getattr(vis, "nodes", None) or []):
    out.append(f"    节点 {n.name}: client.root={n.client.root}  "
               f"base={n.client.base}")

# what the pipeline's server passes
out.append("")
out.append("=== 服务端是怎么建的 ===")
srv = Path(r"E:\dramakit\dramakit\web\server.py").read_text(encoding="utf-8")
import re   # noqa: E402
for m in re.finditer(r"Providers\([^)]*\)", srv):
    out.append("  " + m.group(0))
for m in re.finditer(r"build_pool\([^)]*\)|build_visual\([^)]*\)", srv):
    out.append("  " + m.group(0))
# and in make_context / runner
runner = Path(r"E:\dramakit\dramakit\pipeline\runner.py").read_text(encoding="utf-8")
for m in re.finditer(r"Providers\([^)]*\)", runner):
    out.append("  runner: " + m.group(0))

# Context.__init__
out.append("")
out.append("=== Context.__init__ 里 root 怎么传 ===")
import inspect   # noqa: E402
out.append(inspect.getsource(Context.__init__)[:1500])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\root.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
