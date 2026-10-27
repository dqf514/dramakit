"""Bring the early rounds up to the current code.

Rounds 1 to 6 were shot with an older storyboard, whose shot list did not
say which lines each shot carries and did not give every scene enough
shots. Their video was therefore cut for a different length than the slot
it has to fill, and a few of their scenes have a single long take.

Running the storyboard again gives them the shot list of the current code:
the cut lands on the dialogue, every scene gets the shots its lines need,
and the clips are rendered for the length they actually have.
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
    for s in {stages!r}:
        ep.stage_status.pop(s, None)
    for sc in ep.scenes:
        for sh in sc.shots:
            sh.status = Status.PENDING
            sh.video_path = ''
            sh.prompt = ''
            sh.video_prompt = ''
        if {wipe_shots}:
            sc.shots = []
store.save(proj)
print('{name} 已重置')
"""


def run(cmd, label):
    print(f"--- {label}", flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       errors="replace")
    print("\n".join((r.stdout or "").splitlines()[-10:]), flush=True)
    if r.returncode:
        print("stderr:", (r.stderr or "")[-400:], flush=True)
    return r.returncode


def job(name, stages, wipe_shots):
    project = ROOT / "projects" / name
    if not project.exists():
        print(f"跳过 {name}（不存在）", flush=True)
        return
    run([PY, "-c", RESET.format(name=name, stages=list(stages),
                                 wipe_shots=wipe_shots)], f"重置 {name}")
    run([DJ, "run", str(project), "--stages", ",".join(stages)],
        f"重跑 {name}: {','.join(stages)}")
    run([PY, str(ROOT / "qa.py"), str(project)], f"质检 {name}")
    produced = ROOT / "rounds" / f"{name}.qa.json"
    target = ROOT / "rounds" / "reports" / f"round{name[2:4]}.qa.json"
    if produced.exists():
        produced.replace(target)


if __name__ == "__main__":
    # full = the storyboard is shot again as well; video = only the clips
    for arg in sys.argv[1:]:
        mode, _, name = arg.partition(":")
        if mode == "full":
            job(name, ["storyboard", "promptgen", "visual", "subtitle",
                       "compose", "qc"], True)
        else:
            job(name, ["visual", "subtitle", "compose", "qc"], False)
print("全部完成", flush=True)
