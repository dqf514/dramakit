"""Why did the LLM not answer?

The catalog failed with WinError 10061 - connection refused - which is a
local answer, not a cloud one: reaching an HTTPS host across the network
times out or fails DNS, it does not get refused. So either the resolved
config points somewhere local, or something between the code and the
network is refusing. This reads the config the code actually loads, then
tries the endpoint.
"""
import json
import socket
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, r"E:\dramakit")

out = []

# ---- what config files exist ------------------------------------------
cfgdir = Path(r"E:\dramakit\config")
out.append("=== config/ ===")
for f in sorted(cfgdir.rglob("*")):
    if f.is_file() and f.suffix in (".yaml", ".yml", ".json", ".env"):
        out.append(f"  {f.relative_to(cfgdir)}  {f.stat().st_size} B")

# ---- what the code resolves --------------------------------------------
out.append("")
out.append("=== 实际生效的 LLM 配置 ===")
try:
    from dramakit.config import Config
    cfg = Config()
    llm = cfg.llm
    out.append(f"  provider   : {llm.provider}")
    out.append(f"  base_url   : {llm.base_url}")
    out.append(f"  model      : {llm.model}")
    for attr in ("api_key", "key", "timeout", "max_retries"):
        if hasattr(llm, attr):
            v = getattr(llm, attr)
            if attr in ("api_key", "key") and v:
                v = str(v)[:6] + "…" + f"({len(str(v))} 字符)"
            out.append(f"  {attr:<10}: {v}")
except Exception as e:  # noqa: BLE001
    out.append(f"  读配置失败: {e}")

# ---- is there a key on disk / in env -----------------------------------
out.append("")
out.append("=== 密钥来源 ===")
for k in ("MINIMAX_API_KEY", "OPENAI_API_KEY", "DRAMAKIT_LLM_KEY"):
    v = __import__("os").environ.get(k)
    out.append(f"  env {k}: {'已设 ' + str(len(v)) + ' 字符' if v else '未设'}")
envf = Path(r"E:\dramakit\.env")
out.append(f"  .env 文件: {'存在 ' + str(envf.stat().st_size) + ' B' if envf.exists() else '不存在'}")
if envf.exists():
    for line in envf.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() and not line.strip().startswith("#"):
            key = line.split("=", 1)[0]
            out.append(f"    {key} = …")

# ---- can we reach it? --------------------------------------------------
out.append("")
out.append("=== 连通性 ===")
try:
    from dramakit.config import Config as _C
    base = _C().llm.base_url
except Exception:  # noqa: BLE001
    base = "https://api.minimax.cn/v1"
u = urlparse(base)
out.append(f"  目标: {base}")
out.append(f"  主机: {u.hostname}  端口: {u.port or (443 if u.scheme=='https' else 80)}")
try:
    socket.setdefaulttimeout(10)
    infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80))
    out.append(f"  DNS: 解析到 {len(infos)} 条 -> {infos[0][4][0]}")
except Exception as e:  # noqa: BLE001
    out.append(f"  DNS: 失败 {e}")

try:
    socket.setdefaulttimeout(12)
    s = socket.create_connection((u.hostname, u.port or (443 if u.scheme == "https" else 80)), timeout=12)
    out.append("  TCP: 连上")
    s.close()
except Exception as e:  # noqa: BLE001
    out.append(f"  TCP: 失败 -> {type(e).__name__} {e}")

# ---- and the real request the code would make --------------------------
out.append("")
out.append("=== 真实请求 /v1/chat/completions ===")
try:
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": cfg.llm.model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        out.append(f"  HTTP {r.status}: {r.read().decode('utf-8','replace')[:200]}")
except urllib.error.HTTPError as e:
    out.append(f"  HTTP {e.code}: {e.read().decode('utf-8','replace')[:250]}")
except Exception as e:  # noqa: BLE001
    out.append(f"  失败 -> {type(e).__name__}: {str(e)[:200]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\llmtest.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
