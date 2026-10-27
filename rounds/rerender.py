"""Re-render the shots of the early rounds with the current code.

The video of a shot is cut for the length of its slot, and the slots of
these rounds changed when the timeline learned to cut on the dialogue - so
the clips that are in place were made for a different length and had to be
held still to fill their slot. Rendering them again for the slot they
actually have is the only way that goes away.
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
from dramakit.project import ProjectStore
cfg = Config.load(r'E:\\\\dramakit\\\\config\\\\default.yaml')
root = Path(r'E:\\\\dramakit\\\\projects') / '{name}'
store = ProjectStore(root); proj = store.load()
for ep in proj.episodes:
    for s in ('visual', 'subtitle', 'compose', 'qc'):
        ep.stage_status.pop(s, None)
    for sc in ep.scenes:
        for sh in sc.shots:
            sh.status = __import__('dramakit.models', fromlist=['Status']).Status.PENDING
            sh.video_path = ''
store.save(proj)
print('{name} 已重置')
"""


def run(cmd, label):
    print(f"--- {label}", flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       errors="replace")
    tail = "\n".join((r.stdout or "").splitlines()[-8:])
    print(tail, flush=True)
    return r.returncode


for name in sys.argv[1:]:
    project = ROOT / "projects" / name
    if not project.exists():
        print(f"跳过 {name}（不存在）", flush=True)
        continue
    run([PY, "-c", RESET.format(name=name)], f"重置 {name}")
    run([DJ, "run", str(project), "--stages", "visual,subtitle,compose,qc"],
        f"重出画面并合成 {name}")
    run([PY, str(ROOT / "qa.py"), str(project)], f"质检 {name}")
print("全部完成", flush=True)
