"""Download the bf16 / nvfp4 FLUX 3 fallbacks (for A/B against int8_convrot)."""
import subprocess
import sys
import time
from pathlib import Path

M = Path(r"E:\ComfyUI\models")
COMFY = "ml-resources/flux-3-image-klein-comfy"

JOBS = [
    (COMFY, "text_encoders/qwen3vl_4b_bf16.safetensors", "text_encoders"),
    (COMFY, "diffusion_models/flux3-image-klein-bf16.safetensors", "diffusion_models"),
    (COMFY, "diffusion_models/flux3-image-klein-nvfp4.safetensors", "diffusion_models"),
]

HOSTS = ["https://huggingface.co", "https://hf-mirror.com"]
SUB = 32 * 1024 * 1024
PARALLEL = 6


def head_size(url):
    out = subprocess.run(["curl.exe", "-sIL", "--max-time", "40", url],
                         capture_output=True, text=True, errors="replace").stdout
    size = 0
    for line in out.splitlines():
        if line.lower().startswith("content-length:"):
            try:
                size = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    return size


def grab(url, a, b, part):
    if part.exists() and part.stat().st_size == b - a + 1:
        return True
    for _ in range(6):
        subprocess.run(["curl.exe", "-sL", "--connect-timeout", "20",
                        "--max-time", "400", "-r", f"{a}-{b}",
                        "-o", str(part), url], capture_output=True)
        if part.exists() and part.stat().st_size == b - a + 1:
            return True
    return False


def download(repo, fname, sub):
    dest = M / sub / Path(fname).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"[skip] {dest.name}", flush=True)
        return True
    url = f"{HOSTS[0]}/{repo}/resolve/main/{fname}"
    size = head_size(url)
    if size <= 0:
        url = f"{HOSTS[1]}/{repo}/resolve/main/{fname}"
        size = head_size(url)
    if size <= 0:
        print(f"[FAIL] {fname}: 取不到大小", flush=True)
        return False
    print(f"[get ] {fname} {size/1024**3:.2f} GB", flush=True)
    tmpdir = dest.parent / f".{dest.name}.parts"
    tmpdir.mkdir(parents=True, exist_ok=True)
    ranges = []
    a = 0
    while a < size:
        ranges.append((len(ranges), a, min(a + SUB - 1, size - 1)))
        a = ranges[-1][2] + 1
    t0 = time.time()
    from concurrent.futures import ThreadPoolExecutor, as_completed
    ok = True
    with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        futs = {ex.submit(grab, url, a, b, tmpdir / f"s{i:04d}"): (i, a, b)
                for i, a, b in ranges}
        done = 0
        for fut in as_completed(futs):
            i, a, b = futs[fut]
            ok = fut.result() and ok
            done += 1
            got = sum(p.stat().st_size for p in tmpdir.glob("s*"))
            print(f"   [{done}/{len(ranges)}] {got/1024**3:.2f}/{size/1024**3:.2f} GB  "
                  f"{got/max(time.time()-t0, 0.1)/1024**2:.1f} MB/s", flush=True)
    if not ok:
        print(f"[FAIL] {fname} 分段未完成", flush=True)
        return False
    tmp = dest.with_suffix(dest.suffix + ".assembling")
    with open(tmp, "wb") as out:
        for i, a, b in ranges:
            part = tmpdir / f"s{i:04d}"
            with open(part, "rb") as f:
                while True:
                    buf = f.read(4 * 1024 * 1024)
                    if not buf:
                        break
                    out.write(buf)
            part.unlink(missing_ok=True)
    if tmp.stat().st_size != size:
        print(f"[FAIL] {fname} 大小不符", flush=True)
        return False
    for _ in range(5):
        try:
            if dest.exists():
                dest.unlink()
            tmp.replace(dest)
            break
        except PermissionError:
            time.sleep(2)
    try:
        tmpdir.rmdir()
    except OSError:
        pass
    print(f"[ok  ] {dest.name}", flush=True)
    return True


def main():
    ok = True
    for repo, fname, sub in JOBS:
        ok = download(repo, fname, sub) and ok
    print("ALL DONE" if ok else "SOME FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
