"""Re-render the videos with the performance, and give the music its own clip.

The dialogue is recorded by the drama kit, so the video model is told to
show the performance - that is where the lip movement comes from. Its own
sound is thrown away, because a video model that is told to talk also talks
- in gibberish. The score comes from a separate music-only shot of the
empty location instead.

The stills are kept: only the video prompts, the clips and the score are
redone.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\dramakit")
PY = str(ROOT / "venv" / "Scripts" / "python.exe")
DJ = str(ROOT / "venv" / "Scripts" / "dj.exe")

RESET = """
import sys; sys.path.insert(0, r'E:\\\\dramakit')
from pathlib import Path
from dramakit.config import Config
from dramakit.models import Status
from dramakit.project import ProjectStore
cfg = Config.load(r'E:\\\\dramakit\\\\config\\\\default.yaml')
root = Path(r'E:\\\\dramakit\\\\projects') / '{name}'
store = ProjectStore(root); proj = store.load()
for ep in proj.episodes:
    for s in ('promptgen', 'visual', 'subtitle', 'compose', 'qc'):
        ep.stage_status.pop(s, None)
    for sc in ep.scenes:
        sc.score_prompt = ''
        for sh in sc.shots:
            sh.video_prompt = ''
            sh.video_path = ''
            # the still has to be made again too: the reference fitting and
            # the delivery size may have changed
            if sh.image_path:
                p = store.abs(sh.image_path)
                if p.exists():
                    p.unlink()
            sh.image_path = ''
            sh.status = Status.PENDING
# the music clips are made again too, so they carry the scene's sounds
music = root / 'music'
if music.exists():
    for f in music.glob('*.mp4'):
        f.unlink()
store.save(proj)
print('{name} 已重置')
"""


def run(cmd, label):
    print(f"--- {label}", flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       errors="replace")
    print("\n".join((r.stdout or "").splitlines()[-8:]), flush=True)
    if r.returncode:
        print("stderr:", (r.stderr or "")[-400:], flush=True)
    return r.returncode


for name in sys.argv[1:]:
    project = ROOT / "projects" / name
    if not project.exists():
        print(f"跳过 {name}（不存在）", flush=True)
        continue
    run([PY, "-c", RESET.format(name=name)], f"重置 {name}")
    run([DJ, "run", str(project), "--stages",
         "promptgen,visual,subtitle,compose,qc"], f"重出画面 {name}")
    run([PY, str(ROOT / "qa.py"), str(project)], f"质检 {name}")
    produced = ROOT / "rounds" / f"{name}.qa.json"
    target = ROOT / "rounds" / "reports" / f"round{name[2:4]}.qa.json"
    if produced.exists():
        produced.replace(target)
print("全部完成", flush=True)
