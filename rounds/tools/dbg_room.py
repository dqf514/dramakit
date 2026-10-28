"""Does the room reverb actually work? Look at the waveform."""
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1])
out = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\room.png")
tmp = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode")

for tag, af in (("dry", "aresample=44100"),
                ("room", "aecho=1.0:1.0:38|71:0.224|0.141,aresample=44100")):
    wave = tmp / f"wave_{tag}.png"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
                        af + ",showwavespic=s=900x160:colors=0x40c0ff",
                        "-frames:v", "1", str(wave)], capture_output=True, text=True)
    print(f"{tag}: rc={r.returncode} {r.stderr[:200]}")
    if wave.exists():
        print(f"   波形 {wave}  {wave.stat().st_size} 字节")

# and the loudness
for tag, af in (("dry", "anull"), ("room", "aecho=1.0:1.0:38|71:0.224|0.141")):
    r = subprocess.run(["ffmpeg", "-i", str(src), "-af", af + ",ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True,
                       errors="replace")
    seg = r.stderr[r.stderr.rfind("Summary:"):]
    import re
    m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", seg)
    pk = re.search(r"Peak:\s*(-?[\d.]+)\s*dBFS", seg)
    print(f"{tag}: 响度 {m.group(1) if m else '?'} LUFS  真峰 {pk.group(1) if pk else '?'} dBFS")
