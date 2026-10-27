"""Redo only the music clips of a project.

The score is a separate clip per scene; when the length rule changes, the
pictures do not have to be rendered again.
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
    ep.stage_status.pop('visual', None)
    for sc in ep.scenes:
        for sh in sc.shots:
            sh.status = Status.DONE
store.save(proj)
music = root / 'music'
if music.exists():
    for f in music.glob('*.mp4'):
        f.unlink()
print('{name} 配乐镜头已清空')
"""


def run(cmd, label):
    print(f"--- {label}", flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       errors="replace")
    print("\n".join((r.stdout or "").splitlines()[-8:]), flush=True)
    if r.returncode:
        print("stderr:", (r.stderr or "")[-300:], flush=True)


for name in sys.argv[1:]:
    project = ROOT / "projects" / name
    if not project.exists():
        continue
    run([PY, "-c", RESET.format(name=name)], f"清空 {name} 的配乐镜头")
    run([DJ, "run", str(project), "--stages", "visual,subtitle,compose,qc"],
        f"重出配乐并合成 {name}")
    run([PY, str(ROOT / "qa.py"), str(project)], f"质检 {name}")
    produced = ROOT / "rounds" / f"{name}.qa.json"
    target = ROOT / "rounds" / "reports" / f"round{name[2:4]}.qa.json"
    if produced.exists():
        produced.replace(target)
print("全部完成", flush=True)
