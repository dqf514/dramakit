"""Deep check of the FCPXML hand-off: media present, spine contiguous, lanes."""
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path


def main(path: Path) -> int:
    root = ET.parse(path).getroot()
    bad = 0

    missing = []
    for a in root.findall(".//asset"):
        src = a.get("src") or ""
        if not src.startswith("file:///"):
            continue
        p = Path(urllib.parse.unquote(src[8:]))
        if not p.exists():
            missing.append((a.get("name"), p))
    print(f"资源 {len(root.findall('.//asset'))} 个，缺失 {len(missing)} 个")
    for n, p in missing[:5]:
        print(f"   缺失 {n}: {p}")
    bad += len(missing)

    clips = root.findall(".//spine/asset-clip")
    print(f"主轨片段 {len(clips)} 个")
    off = 0.0
    gaps = 0
    for c in clips:
        o = float(c.get("offset", "0s").rstrip("s"))
        d = float(c.get("duration", "0s").rstrip("s"))
        if abs(o - off) > 0.02:
            gaps += 1
            if gaps <= 3:
                print(f"   主轨不连续：上一段结束 {off:.2f}s，这段从 {o:.2f}s 开始")
        off = max(off, o + d)
    print(f"主轨不连续处: {gaps}   主轨总长 {off:.2f}s")
    bad += gaps

    for sec in root.findall(".//section"):
        name = sec.get("name")
        lc = sec.findall(".//asset-clip")
        print(f"  音轨 {name}: {len(lc)} 段")
        if name == "Dialogue":
            for c in lc[:3]:
                print(f"     offset={c.get('offset')} duration={c.get('duration')}")

    dur = root.find(".//duration")
    if dur is not None:
        print(f"时间线长度: {dur.get('value')}")
    return bad


if __name__ == "__main__":
    p = Path(sys.argv[1])
    sys.exit(0 if main(p) == 0 else 1)
