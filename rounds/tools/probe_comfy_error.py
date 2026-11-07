import json
import urllib.request

base = "http://192.168.31.8:8188"
pid = "c9305853-5686-44d4-904d-55f4bdeb2669"
with urllib.request.urlopen(base + "/history/" + pid, timeout=20) as r:
    h = json.loads(r.read().decode("utf-8"))
entry = h.get(pid) or {}
msgs = (entry.get("status") or {}).get("messages") or []
for kind, data in msgs:
    if kind == "execution_error":
        msg = str(data.get("exception_message") or "")
        print("  长度", len(msg))
        for i in range(0, len(msg), 88):
            print("   ", msg[i:i + 88])
        print("  节点类型：", data.get("node_type"))
