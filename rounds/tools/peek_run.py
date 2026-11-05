"""How the run is doing, and where it is."""
import json
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8080"


def get(p):
    with urllib.request.urlopen(BASE + p, timeout=120) as r:
        return json.loads(r.read())


print("=== 任务 ===")
for j in (get("/api/jobs?limit=12").get("jobs") or []):
    if j.get("kind") != "health":
        print("  %s %-14s %-12s %s" % (j.get("id"), j.get("kind"), j.get("status"),
                                       str(j.get("error") or "")[:70]))

projs = get("/api/projects").get("projects") or []
print()
print("=== 项目 ===")
for p in projs:
    print("  %-16s 集%s 镜%s" % (p.get("slug"), p.get("episodes"), p.get("shots")))
    d = get("/api/progress?project=" + urllib.parse.quote(p["slug"]))
    print("    在飞 %s | 已发起 %s | 完成 %s | 失败 %s | 共计 %s"
          % (d.get("inflight"), d.get("started"), d.get("done"),
             d.get("failed"), d.get("total")))
    print("    道:", d.get("lanes"))
    for k, v in (d.get("stages") or {}).items():
        print("      %-10s 开始%s 在跑%s 完成%s 失败%s 共%s 并发%s"
              % (k, v.get("started"), v.get("running"), v.get("done"),
                 v.get("failed"), v.get("total"), v.get("concurrency")))
    det = get("/api/project?slug=" + urllib.parse.quote(p["slug"]))
    print("    阶段状态:", det.get("stage_status"))
    for ep in det.get("episodes") or []:
        print("      第%d集《%s》%d场%d镜  阶段:%s"
              % (ep.get("index"), ep.get("title"), len(ep.get("scenes") or []),
                 sum(len(s.get("shots") or []) for s in (ep.get("scenes") or [])),
                 {k: v for k, v in (ep.get("stage_status") or {}).items()}))
