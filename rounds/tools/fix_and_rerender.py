"""The shots whose words are in the wrong place are drawn again.

The timeline used to leave a fraction of a millisecond between the end of
one shot and the start of the next, so a line that belongs to a shot landed
in the tail of the shot before it: every line was one shot early, and the
prompt of a shot held the words of its neighbour.

The timeline is fixed.  The prompts that were written against the broken
one are not, so the shots whose words are in the wrong place get a new
prompt and a new clip.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.pipeline.visual import regen_shot
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 1
root = Path(r"E:\\dramakit\\projects") / name
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(root)
proj = store.load()
ep = proj.episode(ep_index)

# the shots whose words are in the wrong place
bad: list[str] = []
for sc in ep.scenes:
    spoken = [l for l in sc.lines if not is_narration(l)]
    for sh in sc.shots:
        owned = {spoken[n - 1].text.strip() for n in (sh.line_indices or [])
                 if 1 <= n <= len(spoken)}
        tags = {t.strip() for t in
                re.findall(r"<d>\[zh-CN\](.*?)</d>", sh.video_prompt or "")}
        if owned and tags != owned:
            bad.append(sh.id)
            print(f"  {sh.id}: 该说 {sorted(owned)}，提示词里 {sorted(tags)}")
print(f"台词错位的片段 {len(bad)} 个")

if not bad:
    sys.exit(0)

# clear their prompts so the promptgen writes them again
for sc in ep.scenes:
    for sh in sc.shots:
        if sh.id in bad:
            sh.video_prompt = ""
store.save(proj)
print("提示词已清空，跑 promptgen 重新生成")

r = subprocess.run([str(Path(r"E:\\dramakit\\venv\\Scripts\\dj.exe")), "run",
                    str(root), "--stages", "promptgen"],
                   cwd=r"E:\\dramakit", capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
print((r.stdout or "")[-300:])

# and draw the shots again
for sid in bad:
    t0 = time.time()
    res = regen_shot(store, cfg, ep_index, sid, mode="video")
    print(f"{sid}: ok={res.get('ok')} 用时 {(time.time()-t0)/60:.1f} 分钟 "
          f"{res.get('error') or ''}", flush=True)
