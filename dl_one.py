"""Fetch one byte range in parallel sub-chunks (large ranges get throttled)."""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

URL = ("https://huggingface.co/ml-resources/flux-3-image-klein-comfy/"
       "resolve/main/text_encoders/qwen3vl_4b_int8_convrot.safetensors")
DEST = Path(r"E:\ComfyUI\models\text_encoders\.qwen3vl_4b_int8_convrot.safetensors.parts\p05")
START = 303659953          # chunk start (absolute byte offset in the file)
END = START + 607319905 - 1
SUB = 32 * 1024 * 1024
PARALLEL = 6


def grab(i: int, a: int, b: int) -> tuple[int, int]:
    part = DEST.with_name(f"p05s{i:02d}")
    if part.exists() and part.stat().st_size == b - a + 1:
        return i, b - a + 1
    for _ in range(8):
        cmd = ["curl.exe", "-sL", "--connect-timeout", "20", "--max-time", "300",
               "-r", f"{a}-{b}", "-o", str(part), URL]
        subprocess.run(cmd, capture_output=True)
        if part.exists() and part.stat().st_size == b - a + 1:
            return i, b - a + 1
    return i, part.stat().st_size if part.exists() else 0


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    ranges = []
    a = START
    while a <= END:
        b = min(a + SUB - 1, END)
        ranges.append((len(ranges), a, b))
        a = b + 1
    t0 = time.time()
    ok = True
    with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        futs = {ex.submit(grab, i, a, b): (i, a, b) for i, a, b in ranges}
        done = 0
        for fut in as_completed(futs):
            i, a, b = futs[fut]
            _, got = fut.result()
            ok = ok and got == b - a + 1
            done += 1
            total = sum(p.stat().st_size for p in DEST.parent.glob("p05s*"))
            print(f"  [{done}/{len(ranges)}] p05s{i:02d} {got/1024**2:.0f}MB  "
                  f"总 {total/1024**2:.0f}MB  "
                  f"{total/max(time.time()-t0, 0.1)/1024**2:.1f} MB/s", flush=True)
    if not ok:
        print("有分段未完成", flush=True)
        return 1
    with open(DEST, "wb") as out:
        for i, _, _ in ranges:
            part = DEST.with_name(f"p05s{i:02d}")
            with open(part, "rb") as f:
                while True:
                    buf = f.read(4 * 1024 * 1024)
                    if not buf:
                        break
                    out.write(buf)
            part.unlink(missing_ok=True)
    print(f"p05 完成 {DEST.stat().st_size/1024**2:.0f}MB", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
