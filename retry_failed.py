"""Re-run the shots that failed, in an existing project.

A single OOM used to take the whole episode down; the retry in the visual
stage now recovers on its own, but a project that was already blocked still
needs its failed shots picked up.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import Status
from dramakit.project import ProjectStore

ROOT = Path(r"E:\dramakit")
PY = str(ROOT / "venv" / "Scripts" / "python.exe")
DJ = str(ROOT / "venv" / "Scripts" / "dj.exe")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--stages", default="visual")
    args = ap.parse_args()

    cfg = Config.load(ROOT / "config" / "default.yaml")
    root = Path(args.project)
    if not root.is_absolute():
        root = ROOT / "projects" / root
    store = ProjectStore(root)
    proj = store.load()

    n = 0
    for ep in proj.episodes:
        failed = [sh for sc in ep.scenes for sh in sc.shots
                  if sh.status == Status.FAILED
                  or (not sh.image_path and not sh.video_path)]
        if not failed:
            continue
        for st in ("visual", "precheck", "compose", "qc"):
            ep.stage_status.pop(st, None)
        for sh in failed:
            sh.status = Status.PENDING
            sh.image_path = ""
            sh.video_path = ""
            n += 1
    store.save(proj)
    print(f"重置 {n} 个失败镜头")

    stages = args.stages
    r = subprocess.run([DJ, "run", str(root), "--stages", stages],
                       cwd=str(ROOT), capture_output=True, text=True,
                       errors="replace")
    tail = "\n".join((r.stdout or "").splitlines()[-25:])
    print(tail)
    print("stderr:", (r.stderr or "")[-400:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
