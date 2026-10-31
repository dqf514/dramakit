"""The whole acceptance pass for a finished episode.

  1. compose + qc        the file itself
  2. verify_episode      every shot has a voice, the subtitles are where the
                         words are, the AI declaration is on the picture
  3. qa.py               the machine's measurements
  4. dj review           a multimodal model watches the episode
  5. dj drift            first frame against last frame, shot by shot
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\\dramakit")
PY = str(ROOT / "venv\\Scripts\\dj.exe")
name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
project = str(ROOT / "projects" / name)


def run(title, cmd, tail=40):
    print("\n" + "=" * 70)
    print("== " + title)
    print("=" * 70)
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    lines = out.splitlines()
    for ln in lines[-tail:]:
        print(ln)
    return out


run("合成 + 质检", [PY, "run", project, "--stages", "subtitle,precheck,compose,qc"], 45)
run("逐镜检查（音轨/台词/字幕/合规）",
    [str(ROOT / "venv\\Scripts\\python.exe"),
     str(ROOT / "rounds\\tools\\verify_episode.py"), name, "1"], 45)
run("机器质检", [str(ROOT / "venv\\Scripts\\python.exe"), str(ROOT / "qa.py"), project], 60)
run("多模态看片", [PY, "review", project, "--frames", "12"], 60)
run("人脸漂移", [PY, "drift", project], 60)
