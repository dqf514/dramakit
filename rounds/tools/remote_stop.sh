#!/bin/bash
echo "=== 队列 ==="
curl -s --max-time 8 http://127.0.0.1:8188/queue > /tmp/q.json
python3 - <<'EOF'
import json
d = json.load(open('/tmp/q.json'))
run = d.get('queue_running') or []
pend = d.get('queue_pending') or []
print('  运行中', len(run), '| 等待', len(pend))
ids = []
for item in run:
    ids.append(item[1] if len(item) > 1 else '')
for item in pend:
    ids.append(item[1] if len(item) > 1 else '')
open('/tmp/qids.txt', 'w').write('\n'.join(str(i) for i in ids if i))
EOF
if [ -s /tmp/qids.txt ]; then
  echo "=== 取消 ==="
  while read -r id; do
    [ -n "$id" ] && curl -s --max-time 8 -X POST "http://127.0.0.1:8188/queue" \
      -H "Content-Type: application/json" -d "{\"delete\":\"$id\"}" >/dev/null && echo "  已取消 $id"
  done < /tmp/qids.txt
fi
sleep 2
echo "=== 之后 ==="
curl -s --max-time 8 http://127.0.0.1:8188/queue > /tmp/q2.json
python3 -c "
import json
d=json.load(open('/tmp/q2.json'))
print('  运行中', len(d.get('queue_running') or []), '| 等待', len(d.get('queue_pending') or []))
"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
