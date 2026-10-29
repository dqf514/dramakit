"""What variants of the H3 model does the official repository publish?"""
import json
import subprocess
import sys

for repo in sys.argv[1:]:
    url = f"https://hf-mirror.com/api/models/{repo}"
    out = subprocess.run(["curl.exe", "-s", "--max-time", "60", url],
                         capture_output=True, text=True, errors="replace").stdout
    try:
        d = json.loads(out.lstrip("\ufeff"))
    except Exception as e:  # noqa: BLE001
        print(repo, "-> 解析失败:", out[:120])
        continue
    if "siblings" not in d:
        print(repo, "->", str(d)[:200])
        continue
    print(f"=== {repo} ===")
    for f in d["siblings"]:
        n = f.get("rfilename", "")
        if n.endswith((".safetensors", ".gguf", ".pt", ".bin", ".json", ".md")):
            print("  ", n)
