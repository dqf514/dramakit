import json
import urllib.request


def get(path):
    with urllib.request.urlopen("http://127.0.0.1:8080" + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


jobs = get("/api/jobs").get("jobs") or []
print("  任务 %d 个" % len(jobs))
for j in jobs:
    print("   %s  %-12s %-28s %s" % (
        j.get("id", "")[:8], j.get("status"), str(j.get("kind")),
        str(j.get("params") or j.get("action") or "")[:70]))
