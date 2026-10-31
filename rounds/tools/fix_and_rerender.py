"""The shots whose words went to the wrong shot are drawn again.

The timeline used to leave a fraction of a millisecond between the end of
one shot and the start of the next, so a line that belongs to a shot landed
in the tail of the shot before it: every line was one shot early, and the
prompt of a shot held the words of its neighbour.

The timeline is fixed.  The prompts that were written against the broken
one are not, so the shots whose words are in the wrong place get a new
prompt and a new clip.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.visual import regen_shot
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 1
root = Path(r"E:\\dramakit\\projects") / name
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(root)
ctx = Context(cfg, store)
ep = ctx.project.episode(ep_index)

# the shots whose words are in the wrong place
bad: list[str] = []
for sc in ep.scenes:
    spoken = [l for l in sc.lines if l.kind.value != "narration"]
    for sh in sc.shots:
        owned = [spoken[n - 1] for n in (sh.line_indices or [])
                 if 1 <= n <= len(spoken)]
        vp = sh.video_prompt or ""
        if not owned:
            continue
        if any(l.text not in vp for l in owned):
            bad.append(sh.id)
        # and the ones that hold a line that is not theirs
        for other in ep.scenes:
            for o in other.lines:
                pass
print(f"台词错位的片段 {len(bad)} 个：{bad}")

# clear their prompts so the promptgen writes them again
proj = store.load()
ep2 = proj.episode(ep_index)
for sc in ep2.scenes:
    for sh in sc.shots:
        if sh.id in bad:
            sh.video_prompt = ""
store.save(proj)
print("提示词已清空，跑 promptgen 重新生成")

r = subprocess.run([str(Path(r"E:\\dramakit\\venv\\Scripts\\dj.exe")), "run",
                    str(root), "--stages", "promptgen"],
                   cwd=r"E:\\dramakit", capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
print((r.stdout or "")[-400:])

# and draw the shots again
for sid in bad:
    t0 = time.time()
    res = regen_shot(store, cfg, ep_index, sid, mode="video")
    print(f"{sid}: ok={res.get('ok')} 用时 {(time.time()-t0)/60:.1f} 分钟 "
          f"{res.get('error') or ''}", flush=True)
