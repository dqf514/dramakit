"""Start a run through the console and watch it.

The console is the door a person knocks on, so the run is started the
way the page starts it, and the answer is watched the same way.
"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8080"
SLUG = "穿成亿万总裁他前妻"


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    stages = sys.argv[1].split(",")
    episodes = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else []
    body = {"project": SLUG, "chapters": [], "stages": stages}
    if episodes:
        body["episodes"] = episodes
    print("  起跑：%s  集%s" % (stages, episodes or "全部"))
    started = post("/api/run", body)
    print("  接了活：%s" % json.dumps(started, ensure_ascii=False)[:200])
    job = started.get("job")
    if not job:
        return 1
    seen = 0
    last = time.time()
    while True:
        time.sleep(3)
        lines = get("/api/logs?n=300").get("lines") or []
        for l in lines[seen:]:
            msg = str(l.get("msg", ""))
            if msg.strip():
                print("   [%s] %s" % (l.get("lv"), msg[:190]))
        seen = len(lines)
        j = get("/api/jobs?id=" + job)
        if j.get("status") in ("done", "failed", "error", "interrupted"):
            print("  跑完了：%s" % j.get("status"))
            print("  %s" % json.dumps(j.get("result") or {}, ensure_ascii=False)[:900])
            if j.get("error"):
                print("  出错：%s" % str(j.get("error"))[:500])
            return 0 if j.get("status") == "done" else 1
        if time.time() - last > 30:
            last = time.time()
            print("   ... 还在跑（%s）" % j.get("status"))


if __name__ == "__main__":
    sys.exit(main())
