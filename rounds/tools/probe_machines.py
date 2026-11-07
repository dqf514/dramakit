"""Are the cards awake?

Three machines make the pictures: the one here, and the two 3090s
across the room.  Each one is asked the same question - is it
answering, and what does it say it has.
"""
import json
import urllib.request

MACHINES = [
    ("本机 5080", "http://127.0.0.1:8188"),
    ("3090-a", "http://192.168.31.8:8188"),
    ("3090-b", "http://192.168.31.8:8189"),
]

for label, base in MACHINES:
    print("===", label, base)
    try:
        with urllib.request.urlopen(base + "/system_stats", timeout=8) as r:
            d = json.loads(r.read().decode("utf-8"))
        dev = d.get("devices") or []
        for g in dev:
            print("   显卡 %s  显存 %.1f/%.1f GB" %
                  (g.get("name", "?")[:28], (g.get("vram_free", 0) or 0) / 1e9,
                   (g.get("vram_total", 0) or 0) / 1e9))
    except Exception as e:  # noqa: BLE001
        print("   问不到：%s" % str(e)[:90])
        continue
    try:
        with urllib.request.urlopen(base + "/queue", timeout=8) as r:
            q = json.loads(r.read().decode("utf-8"))
        print("   队列：跑着 %d，待跑 %d"
              % (len(q.get("queue_running") or []), len(q.get("queue_pending") or [])))
    except Exception as e:  # noqa: BLE001
        print("   队列问不到：%s" % str(e)[:70])
    try:
        with urllib.request.urlopen(base + "/models", timeout=10) as r:
            m = json.loads(r.read().decode("utf-8"))
        for k, v in m.items():
            print("   模型 %-14s %s" % (k, ", ".join(v) if isinstance(v, list) else v))
    except Exception as e:  # noqa: BLE001
        print("   模型问不到：%s" % str(e)[:70])
