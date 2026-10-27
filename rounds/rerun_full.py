"""Run a project through the whole pipeline again, from the storyboard down.

The script and the cast stay - the point is to see the same story shot
again with the current code, so the difference between the episodes is the
pipeline and not the story. The storyboard, the prompts, the pictures, the
videos, the music and the cut are all made again.
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
    for s in ('storyboard', 'promptgen', 'voice', 'visual', 'subtitle',
              'music', 'precheck', 'compose', 'qc'):
        ep.stage_status.pop(s, None)
    for sc in ep.scenes:
        sc.shots = []
        sc.score_prompt = ''
store.save(proj)
print('{name} 已重置（剧本与定妆保留）')
"""

STAGES = ("storyboard,promptgen,voice,visual,subtitle,music,precheck,"
          "compose,qc")


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
    run([DJ, "run", str(project), "--stages", STAGES], f"全流水线 {name}")
    run([PY, str(ROOT / "qa.py"), str(project)], f"质检 {name}")
    produced = ROOT / "rounds" / f"{name}.qa.json"
    target = ROOT / "rounds" / "reports" / f"round{name[2:4]}.qa.json"
    if produced.exists():
        produced.replace(target)
print("全部完成", flush=True)
