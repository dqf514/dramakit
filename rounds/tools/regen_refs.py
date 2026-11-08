"""Regenerate the character and location reference images with FLUX 3.

The existing ones were made by SDXL with a keyword prompt, and FLUX 3 read
"character reference sheet" literally - it came back as technical line art
instead of a person. Delete the files and re-run the character stage; the LLM
anchors stay untouched.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\dramakit\projects\测试短剧")


def main() -> int:
    n = 0
    for pat in ("characters/*/*.png", "locations/*/*.png"):
        for p in ROOT.glob(pat):
            p.unlink(missing_ok=True)
            n += 1
    print(f"删除旧参考图 {n} 个")
    r = subprocess.run(
        [r"E:\dramakit\venv\Scripts\dj.exe", "run", str(ROOT.parent / ROOT.name),
         "--stages", "character"],
        cwd=r"E:\dramakit", capture_output=True, text=True, errors="replace")
    print(r.stdout[-3000:])
    print(r.stderr[-1500:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
