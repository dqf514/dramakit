"""Put a frame from each clip side by side, and say which card made it.

"Quality has a problem" is a claim about pictures, so the pictures are
what gets looked at: one frame from a clip the remote card made, one
from a clip the local card made, at the same size, side by side.

The card that made a clip is in the card's own history, so it is read
from there rather than guessed from the time of day.
"""
import json
import subprocess
import urllib.request
from pathlib import Path

OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\quality")
OUT.mkdir(parents=True, exist_ok=True)
PROJ = Path(r"E:\dramakit\projects\星际骷髅兵")

HOSTS = [("远端 3090-a", "http://192.168.31.8:8188"),
         ("远端 3090-b", "http://192.168.31.8:8189"),
         ("本机 5080", "http://127.0.0.1:8188")]


def cards():
    """Which card made which clip."""
    out = {}
    for label, host in HOSTS:
        try:
            with urllib.request.urlopen(f"{host}/history?max_items=40", timeout=60) as r:
                hist = json.loads(r.read())
        except Exception:  # noqa: BLE001
            continue
        for pid, rec in hist.items():
            p = rec.get("prompt")
            g = p[2] if isinstance(p, list) and len(p) > 2 else {}
            if not any("ReferenceToVideo" in str(n.get("class_type", "")) for n in g.values()):
                continue
            unet = ""
            for n in g.values():
                if n.get("class_type") == "UNETLoader":
                    unet = str((n.get("inputs") or {}).get("unet_name"))
            out[pid] = (label, unet)
    return out


def frame(video: Path, dest: Path, at="00:00:03"):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", at, "-i", str(video),
                    "-frames:v", "1", "-vf", "scale=960:-1", str(dest)],
                   capture_output=True, timeout=120)


def main():
    made = cards()
    print("=== 卡上记录的片 ===")
    for pid, (label, unet) in list(made.items())[:12]:
        print(f"  {pid[:10]}  {label:12} {unet}")

    vids = sorted([f for f in (PROJ / "video").rglob("*.mp4") if f.is_file()],
                  key=lambda x: x.stat().st_mtime)
    print(f"\n=== 工程里的片 {len(vids)} 段 ===")
    for v in vids:
        print(f"  {v.name:28} {v.stat().st_mtime:.0f} {v.stat().st_size/1048576:.1f} MB")

    # one frame from the first (remote-era) and the last (local-era) clips
    picks = []
    if len(vids) >= 2:
        picks = [("早的（远端时代）", vids[0]), ("晚的（本机时代）", vids[-1])]
    imgs = []
    for label, v in picks:
        dest = OUT / (label.split("（")[0] + "_" + v.stem + ".jpg")
        frame(v, dest)
        if dest.exists():
            imgs.append((label, v, dest))
            print(f"\n  {label}: {v.name} -> {dest.name}")

    if imgs:
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for _l, _v, im in imgs:
            cmd += ["-i", str(im)]
        out = OUT / "对比.jpg"
        cmd += ["-filter_complex", "hstack=inputs=2", str(out)]
        subprocess.run(cmd, capture_output=True, timeout=120)
        print("\n  并排:", out, "->", out.exists())


if __name__ == "__main__":
    main()
