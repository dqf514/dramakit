#!/bin/bash
echo "=== 输出目录 ==="
ls -lt /data/comfyui/output/dramakit/ 2>/dev/null | head -14
echo
echo "=== 最新文件的流 ==="
for f in $(ls -t /data/comfyui/output/dramakit/* 2>/dev/null | head -6); do
  echo "== $f"
  ffprobe -v error -show_entries stream=codec_type,codec_name,width,height -of csv=p=0 "$f" 2>&1 | head -4
done
echo
echo "=== history 里某个 prompt 的 outputs 结构 ==="
curl -s --max-time 10 "http://127.0.0.1:8188/history?max_items=2" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for pid, h in list(d.items())[:2]:
    print('prompt', pid)
    for nid, o in (h.get('outputs') or {}).items():
        print('  node', nid, 'keys:', list(o.keys()))
        for k, items in o.items():
            if isinstance(items, list):
                for it in items:
                    print('    ', k, '->', {kk: str(vv)[:60] for kk, vv in it.items() if kk in ('filename','subfolder','type','format')})
"
