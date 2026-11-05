"""Patch a file that keeps its line endings.

The repository is checked out with CRLF, and the editing tool writes LF -
so a multi-line replacement has to be written with the line endings the
file already has.  This script takes a JSON list of [path, old, new]
pairs, matches the old text with either ending, and writes the file back
with the ending it had.
"""
import json
import sys
from pathlib import Path


def patch(path: str, old: str, new: str) -> bool:
    p = Path(path)
    raw = p.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    o = old.replace("\n", "\r\n") if crlf else old
    n = new.replace("\n", "\r\n") if crlf else new
    if o not in text:
        o2 = old.replace("\n", "\r\n") if not crlf else old
        n2 = new.replace("\n", "\r\n") if not crlf else new
        if o2 not in text:
            return False
        o, n = o2, n2
    p.write_bytes(text.replace(o, n, 1).encode("utf-8"))
    return True


def main() -> int:
    pairs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    bad = 0
    for path, old, new in pairs:
        if not patch(path, old, new):
            print(f"NO MATCH: {path}")
            print("  " + old.splitlines()[0][:90])
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
