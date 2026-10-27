"""Read the rhythm off a reference video.

A short drama that works is worth copying: how fast it cuts, how long the
opening holds before the first line, how long the shots are. This measures
that on a finished video so the storyboard can be told to cut like it.

    dj ref-rhythm 参考片.mp4
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(add_completion=False, help="参考片的节奏分析")
console = Console()


def _cuts(path: Path) -> list[float]:
    """The times where the picture changes."""
    r = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-vf",
         "select='gt(scene,0.25)',showinfo", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace")
    times = []
    for m in re.finditer(r"pts_time:([\d.]+)", r.stderr):
        try:
            times.append(float(m.group(1)))
        except ValueError:
            pass
    return times


def _duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def analyse(path: Path) -> dict:
    dur = _duration(path)
    raw = sorted(set(round(t, 2) for t in _cuts(path)))
    # a transition fades to black and back, which the detector sees as two
    # cuts; they are one cut
    cuts: list[float] = []
    for t in raw:
        if cuts and t - cuts[-1] < 0.5:
            continue
        cuts.append(t)
    bounds = [0.0] + cuts + [dur]
    lengths = [round(bounds[i + 1] - bounds[i], 2) for i in range(len(bounds) - 1)]
    lengths = [x for x in lengths if x > 0.15]
    if not lengths:
        return {"source": str(path), "duration": dur, "shots": 0}
    ordered = sorted(lengths)
    mid = len(ordered) // 2

    def pct(p: float) -> float:
        return ordered[min(len(ordered) - 1, int(len(ordered) * p))]

    # the opening: how long before the first cut
    first = lengths[0]
    # how many cuts in the first three seconds
    early = sum(1 for t in cuts if t <= 3.0)
    profile = {
        "source": path.name,
        "duration": round(dur, 2),
        "shots": len(lengths),
        "avg_shot": round(sum(lengths) / len(lengths), 2),
        "median_shot": ordered[mid],
        "min_shot": round(ordered[0], 2),
        "max_shot": round(ordered[-1], 2),
        "p25_shot": pct(0.25),
        "p75_shot": pct(0.75),
        "opening_shot": round(first, 2),
        "cuts_first_3s": early,
        "cuts_per_min": round(len(cuts) / max(dur / 60.0, 1e-6), 1),
        "cut_times": cuts[:120],
        "shot_lengths": lengths[:120],
    }
    return profile


@app.command()
def rhythm(
    video: str = typer.Argument(..., help="参考片视频文件"),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="写出 JSON 的路径"),
    apply: bool = typer.Option(False, "--apply", help="写成流水线默认的节奏参考"),
) -> None:
    """分析参考片的剪辑节奏。"""
    path = Path(video)
    if not path.exists():
        console.print(f"[red]找不到文件：{path}[/red]")
        raise typer.Exit(1)
    p = analyse(path)
    console.print(f"[bold]{p['source']}[/bold]  {p.get('duration', 0):.1f}s  "
                  f"{p.get('shots', 0)} 个镜头")
    if p.get("shots"):
        console.print(f"  平均 {p['avg_shot']}s  中位 {p['median_shot']}s  "
                      f"最短 {p['min_shot']}s  最长 {p['max_shot']}s")
        console.print(f"  开场第一个镜头 {p['opening_shot']}s  "
                      f"前 3 秒切了 {p['cuts_first_3s']} 次  "
                      f"每分钟 {p['cuts_per_min']} 刀")
    target = Path(out) if out else Path("config/ref_rhythm.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]已写出 {target}[/green]")
    if apply and p.get("shots"):
        _apply(p, target)


def _apply(profile: dict, path: Path) -> None:
    """Store the profile where the storyboard will read it."""
    from .config import Config
    cfg_path = Path("config/default.yaml")
    if not cfg_path.exists():
        return
    text = cfg_path.read_text(encoding="utf-8")
    block = (f"  # 拉片结果：{profile['source']} 平均 {profile['avg_shot']}s/镜"
             f" 开场 {profile['opening_shot']}s 每分钟 {profile['cuts_per_min']} 刀\n"
             f"  ref_rhythm: {json.dumps(profile, ensure_ascii=False)}\n")
    text = re.sub(r"  # 拉片结果：.*?\n  ref_rhythm: .*?\n", block, text,
                  flags=re.S)
    if "ref_rhythm:" not in text:
        text = text.replace("storyboard:\n", "storyboard:\n" + block)
    cfg_path.write_text(text, encoding="utf-8")
    console.print(f"[green]已写入 {cfg_path} 的 storyboard.ref_rhythm[/green]")


if __name__ == "__main__":
    app()
