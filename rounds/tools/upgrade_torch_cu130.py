"""Put the card's own torch build in place.

The card is a Blackwell, and Blackwell has fourth-bit tensor cores.
ComfyUI can use them - through the quantised kernels in comfy-kitchen -
but only with a PyTorch built against CUDA 13. The build that is
installed is a CUDA 12.8 one, so the fast kernels are turned off and
every quantised weight is unpacked by hand on every step: the card
shows as busy, draws a fraction of the power it could, and runs at a
quarter of the speed.

The build that goes in is the same version, the same torchvision, the
same torchaudio - only the CUDA they are built against changes. The old
wheels are kept on disk, so putting it back is one command.
"""
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MIRROR = "https://mirrors.aliyun.com/pytorch-wheels/cu130/"
WHEELS = [
    ("torch", "2.11.0"),
    ("torchvision", "0.26.0"),
    ("torchaudio", "2.11.0"),
]
PY = r"E:\ComfyUI\venv\Scripts\python.exe"
DL = Path(r"E:\dramakit\rounds\tools\wheelhouse")
PY_TAG = "cp312-cp312-win_amd64"


def note(msg):
    print(msg, flush=True)


def listing():
    with urllib.request.urlopen(MIRROR, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    out = {}
    for m in re.finditer(
            r'(torchvision|torchaudio|torch)-([0-9.]+)(?:%2B|&#43;|\+)(cu\d+)-'
            r'cp312-cp312-win_amd64\.whl', html):
        out[(m.group(1), m.group(2), m.group(3))] = m.group(0)
    return out


def main():
    DL.mkdir(parents=True, exist_ok=True)
    have = listing()
    note("=== 下载轮子 ===")
    files = []
    for pkg, ver in WHEELS:
        name = have.get((pkg, ver, "cu130"))
        if not name:
            note("  %s %s+cu130 找不到！" % (pkg, ver))
            return 1
        url = MIRROR + name.replace("&#43;", "%2B")
        dest = DL / name.replace("&#43;", "+")
        if not dest.exists() or dest.stat().st_size < 1000:
            t0 = time.time()
            note("  下载 %s" % dest.name)
            try:
                with urllib.request.urlopen(url, timeout=120) as r, dest.open("wb") as f:
                    got = 0
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
            except Exception as e:  # noqa: BLE001
                note("  下载失败: %s %s" % (type(e).__name__, str(e)[:120]))
                return 1
            note("    完成 %.2f GB（%.0f 秒）" % (dest.stat().st_size / 2**30,
                                               time.time() - t0))
        else:
            note("  已有 %s" % dest.name)
        files.append(str(dest))

    note("=== 装上 ===")
    # --no-deps: everything torch needs is already in this venv, and a
    # fresh resolve could pull a different numpy under it
    cmd = [PY, "-m", "pip", "install", "--no-deps", "--force-reinstall"] + files
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=3600)
    for line in (r.stdout or "").split("\n")[-8:]:
        if line.strip():
            note("  " + line.strip()[:140])
    if r.returncode != 0:
        note("  装失败：")
        for line in (r.stderr or "").split("\n")[-10:]:
            if line.strip():
                note("  " + line.strip()[:140])
        return 1

    note("=== 装完是什么版本 ===")
    r = subprocess.run([PY, "-c",
                        "import torch;print(torch.__version__, torch.version.cuda, "
                        "torch.cuda.get_device_capability())"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    note("  " + (r.stdout or r.stderr).strip()[:200])
    note("=== 回退用的旧轮子也留着 ===")
    for pkg, ver in WHEELS:
        name = have.get((pkg, ver, "cu128"))
        if not name:
            continue
        dest = DL / name.replace("&#43;", "+")
        if not dest.exists():
            url = MIRROR.replace("cu130", "cu128") + name.replace("&#43;", "%2B")
            try:
                with urllib.request.urlopen(url, timeout=120) as rr, dest.open("wb") as f:
                    while True:
                        chunk = rr.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                note("  已留 %s（%.2f GB）" % (dest.name, dest.stat().st_size / 2**30))
            except Exception as e:  # noqa: BLE001
                note("  %s 留不下来: %s" % (dest.name, type(e).__name__))
    return 0


if __name__ == "__main__":
    sys.exit(main())
