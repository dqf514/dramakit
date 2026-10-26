"""One iteration: build a project from the round's script, run the whole
pipeline, then QA the result and write the report.

    python round.py --round 3

Everything stays on disk: the project under projects/, the script under
rounds/scripts/, the report under rounds/reports/.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"E:\dramakit")
ROUNDS = ROOT / "rounds"
PY = str(ROOT / "venv" / "Scripts" / "python.exe")
DJ = str(ROOT / "venv" / "Scripts" / "dj.exe")


def run(cmd, log: Path, label: str) -> int:
    print(f"--- {label}", flush=True)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(f"\n\n===== {label} =====\n")
        fh.flush()
        p = subprocess.run(cmd, cwd=str(ROOT), stdout=fh, stderr=subprocess.STDOUT,
                           text=True, errors="replace")
    print(f"    exit={p.returncode}  日志 {log.name}", flush=True)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--stages", default="")
    args = ap.parse_args()

    n = args.round
    script = ROUNDS / "scripts" / f"round{n:02d}.txt"
    if not script.exists():
        print(f"没有剧本: {script}")
        return 2
    name = f"轮次{n:02d}_{script.stem.replace('round', '').replace('_', '')}"
    project = ROOT / "projects" / name
    log = ROUNDS / "logs" / f"round{n:02d}.log"
    report = ROUNDS / "reports" / f"round{n:02d}.qa.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    if not project.exists():
        run([DJ, "new", name, "--source", str(script)], log, "创建项目")
    else:
        print(f"项目已存在，复用: {project}")

    stages = args.stages or "ingest,analyze,character,segment,script,storyboard,promptgen,visual,voice,subtitle,music,precheck,compose,qc"
    t0 = time.time()
    rc = run([DJ, "run", str(project), "--stages", stages], log, "跑流水线")
    print(f"--- 流水线用时 {(time.time()-t0)/60:.1f} 分钟", flush=True)

    run([PY, str(ROOT / "qa.py"), str(project)], log, "质检")
    # qa.py writes rounds/<project>.qa.json - copy it to the round's name
    produced = ROUNDS / f"{project.name}.qa.json"
    if produced.exists():
        produced.replace(report)
        print(f"报告: {report}")
    else:
        print("没有质检报告")
        return 3
    return rc


if __name__ == "__main__":
    sys.exit(main())
