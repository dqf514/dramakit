"""What did H3 say in every clip? Check it against the script."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects") / name))
ep = ctx.target_episodes()[0]
tl = ctx.timeline(ep)

py = r"E:\\ComfyUI\\venv\\Scripts\\python.exe"
tr = r"E:\\dramakit\\rounds\\tools\\transcribe3.py"
ok = bad = 0
for tsc in tl.scenes:
    for ts in tsc.shots:
        shot = ts.shot
        if not shot.video_path:
            continue
        clip = ctx.store.abs(shot.video_path)
        if not clip.exists():
            continue
        want = [t.line.text for t in tsc.lines
                if t.line.kind.value == "dialogue"
                and ts.start - 0.02 <= t.start < ts.start + ts.duration]
        if not want:
            continue
        r = subprocess.run([py, tr, str(clip)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        said = ""
        for line in r.stdout.splitlines():
            if line.startswith("原样:"):
                said = line.split(":", 1)[1].strip()
        target = "".join(want)
        chars = set(target)
        hit = sum(1 for c in chars if c in said) / max(len(chars), 1)
        extra = "".join(c for c in said if c not in target and c.strip())
        mark = "OK " if hit > 0.6 else "!! "
        ok += hit > 0.6
        bad += hit <= 0.6
        print(f"{mark}{shot.id} 要说「{target}」 H3说「{said}」"
              + (f" 多出来的:「{extra}」" if extra else ""))
print(f"\n对得上 {ok} 镜，对不上 {bad} 镜")
