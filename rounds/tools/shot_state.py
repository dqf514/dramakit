"""Every shot: status, video path, and whether the file is really there."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"E:\dramakit\projects\短剧_重生恶毒继母")
d = json.loads((root / "project.json").read_text(encoding="utf-8"))
print("project keys:", list(d.keys()))
for ep in d.get("episodes", []):
    print(f"=== 第{ep.get('index')}集 {ep.get('title')} status={ep.get('status')}")
    for sc in ep.get("scenes", []):
        for sh in sc.get("shots", []):
            vp = sh.get("video_path") or ""
            f = (root / vp) if vp else None
            print(f"  {sh.get('id')}  {sh.get('status'):<8} vp={vp or '(空)':<44}"
                  f"存在={f.exists() if f else '-'}  meta={list((sh.get('gen_meta') or {}).keys())}")
