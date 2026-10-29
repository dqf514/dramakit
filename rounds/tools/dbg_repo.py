"""What is in the Abiray H3 repository, and how big is each file?"""
import json
import subprocess
import sys


def files(repo):
    url = f"https://hf-mirror.com/api/models/{repo}?blobs=true"
    out = subprocess.run(["curl.exe", "-s", "--max-time", "90", url],
                         capture_output=True, text=True, errors="replace").stdout
    d = json.loads(out.lstrip("\ufeff"))
    rows = []
    for f in d.get("siblings", []):
        n = f.get("rfilename", "")
        sz = f.get("size") or 0
        rows.append((n, sz))
    return rows


for repo in sys.argv[1:]:
    print(f"=== {repo}")
    try:
        rows = files(repo)
    except Exception as e:  # noqa: BLE001
        print("   取不到:", e)
        continue
    total = 0
    for n, sz in sorted(rows, key=lambda r: -r[1]):
        if not n.endswith((".safetensors", ".gguf", ".pt", ".pth")):
            continue
        total += sz
        print(f"   {sz/1e9:7.2f} GB  {n}")
    print(f"   —— 合计 {total/1e9:.1f} GB")
    print()
