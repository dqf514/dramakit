"""Verify a safetensors file's header and size."""
import json
import struct
import sys
from pathlib import Path


def check(p: Path) -> bool:
    with open(p, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
    tensors = [k for k in header if k != "__metadata__"]
    total = 0
    for k in tensors:
        s, e = header[k]["data_offsets"]
        total = max(total, e)
    expected = 8 + n + total
    actual = p.stat().st_size
    ok = expected == actual
    print(f"{'OK ' if ok else 'BAD'} {p.name}")
    print(f"    tensors={len(tensors)} header={n}B 数据区={total/1024**3:.2f}GB "
          f"期望={expected} 实际={actual}")
    return ok


if __name__ == "__main__":
    allok = True
    for a in sys.argv[1:]:
        allok = check(Path(a)) and allok
    sys.exit(0 if allok else 1)
