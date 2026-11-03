"""The node page's three calls, against the running console.

The page asks for the fleet, then for each card the weights it actually
has and which loader each override names, then writes a change back. All
three are exercised here against the live console, because the second one
reads the card over the network and the third one writes the config file
that everything else reads.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
out = []


def get(path, timeout=60):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


def post(path, payload, timeout=60):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


# --- 1. the fleet ------------------------------------------------------
out.append("=== GET /api/nodes ===")
st, r = get("/api/nodes")
out.append(f"  HTTP {st}  ok={r.get('ok')}")
out.append(f"  工作流清单 {len(r.get('workflows') or [])} 个: {r.get('workflows')}")
for n in r.get("nodes") or []:
    c = n.get("config") or {}
    out.append(f"  {n['name']:12} online={n.get('online')} roles={n.get('roles')} "
               f"base={n.get('base_url')}")
    out.append(f"      config 键: {sorted(c)[:12]}")
    out.append(f"      overrides: {c.get('graph_overrides')}")
    out.append(f"      workflows: {c.get('workflows')}")

# --- 2. the weights each card has ---------------------------------------
out.append("")
out.append("=== GET /api/nodes/models?node=... ===")
for n in (r.get("nodes") or []):
    st2, r2 = get("/api/nodes/models?node=" + urllib.parse.quote(n["name"]))
    out.append(f"  {n['name']}: HTTP {st2} ok={r2.get('ok')}")
    if not r2.get("ok"):
        out.append(f"      {r2.get('error')}")
        continue
    files = r2.get("files") or {}
    for cls, lst in files.items():
        out.append(f"      {cls}: {len(lst)} 个  {lst[:3]}")
    out.append(f"      kinds: {r2.get('kinds')}")
    out.append(f"      当前 overrides: {r2.get('overrides')}")
    out.append(f"      该卡的工作流: {r2.get('workflow')}")

# --- 3. write it back --------------------------------------------------
out.append("")
out.append("=== POST /api/nodes/save（改一个无害的值再改回）===")
target = next((n for n in (r.get("nodes") or [])
               if n.get("online") and (n.get("config") or {}).get("base_url")), None)
if target:
    cfg = dict(target.get("config") or {})
    name = cfg.get("name")
    before_url = cfg.get("base_url")
    probe = "http://127.0.0.1:1/probe"
    st3, r3 = post("/api/nodes/save", {"nodes": [
        {"name": name, "base_url": probe}]})
    out.append(f"  写入探测值: HTTP {st3} ok={r3.get('ok')}")
    # read it back
    st4, r4 = get("/api/nodes")
    got = next((n for n in (r4.get("nodes") or [])
                if (n.get("config") or {}).get("name") == name), None)
    out.append(f"  读回 base_url = {(got or {}).get('config', {}).get('base_url')}")
    # put it back
    st5, r5 = post("/api/nodes/save", {"nodes": [
        {"name": name, "base_url": before_url}]})
    out.append(f"  还原: HTTP {st5} ok={r5.get('ok')}")
    st6, r6 = get("/api/nodes")
    got2 = next((n for n in (r6.get("nodes") or [])
                  if (n.get("config") or {}).get("name") == name), None)
    out.append(f"  最终 base_url = {(got2 or {}).get('config', {}).get('base_url')}")
else:
    out.append("  没有在线节点可试")

# --- the config on disk ------------------------------------------------
out.append("")
out.append("=== 磁盘上的配置 ===")
import yaml   # noqa: E402
cfg = yaml.safe_load(Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8"))
for n in cfg["comfyui"]["nodes"]:
    out.append(f"  {n['name']}: enabled={n.get('enabled')} {n.get('base_url')} "
               f"overrides={list((n.get('graph_overrides') or {}))} "
               f"workflows={n.get('workflows')}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\nodepage.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
