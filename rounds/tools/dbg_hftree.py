import json
import subprocess
import sys

for repo in sys.argv[1:]:
    url = f"https://hf-mirror.com/api/models/{repo}"
    out = subprocess.run(["curl.exe", "-s", "--max-time", "40", url],
                         capture_output=True, text=True, errors="replace").stdout
    try:
        d = json.loads(out.lstrip("\ufeff"))
    except Exception as e:  # noqa: BLE001
        print(repo, "-> 解析失败", out[:80])
        continue
    sib = [f.get("rfilename", "") for f in d.get("siblings", [])]
    hit = [n for n in sib if n.endswith(".pth") or "bisen" in n.lower()]
    print(f"{repo}: {len(sib)} 个文件  候选: {hit[:6]}")
