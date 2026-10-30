#!/bin/bash
echo "=== 最近两个任务的参考图槽位 ==="
curl -s --max-time 15 "http://127.0.0.1:8188/history?max_items=2" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for pid, h in list(d.items())[:2]:
    print('prompt', pid)
    p = h.get('prompt') or []
    graph = p[2] if len(p) > 2 else {}
    for nid, node in graph.items():
        if node.get('class_type') == 'LoadImage':
            print('   node', nid, '->', node['inputs'].get('image'))
        if node.get('class_type') == 'LoadAudio':
            print('   node', nid, '(audio) ->', node['inputs'].get('audio'))
    for nid, node in graph.items():
        if node.get('class_type') == 'MiniMaxH3ReferenceToVideo':
            print('   ref_images:', json.dumps(node['inputs'].get('ref_images'), ensure_ascii=False))
            print('   ref_audios:', json.dumps(node['inputs'].get('ref_audios'), ensure_ascii=False))
            print('   length:', node['inputs'].get('length'), 'size:', node['inputs'].get('width'), 'x', node['inputs'].get('height'))
            pr = node['inputs'].get('prompt','')
            print('   prompt head:', pr[:200].replace(chr(10),' | '))
"
echo
echo "=== input 目录里最近的文件 ==="
ls -lt /data/comfyui/input/ | head -12
