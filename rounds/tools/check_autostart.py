"""Is the machine bringing the stack up with it?

Three questions, in the order they matter:
  - is the scheduled task there, and what did it do the last time
  - are the two services answering right now
  - did the boot trigger actually fire (the log says when the machine
    last started, and every autostart run says so too)

    python rounds/tools/check_autostart.py
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOG = ROOT / "logs" / "autostart" / "autostart.log"
TASK = "DramaKit Stack"


def ps(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"({e})"


def http(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            body = r.read()
            return r.status == 200, f"{r.status} · {len(body)} 字节"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def main() -> int:
    print("== 服务 ==")
    ok_c, why_c = http("http://127.0.0.1:8188/queue")
    ok_d, why_d = http("http://127.0.0.1:8080/api/health")
    print(f"  ComfyUI 8188   {'在跑' if ok_c else '没跑'}   {why_c}")
    print(f"  控制台 8080    {'在跑' if ok_d else '没跑'}   {why_d}")

    print("\n== 计划任务 ==")
    out = ps(["schtasks", "/query", "/tn", TASK, "/fo", "LIST", "/v"])
    if "ERROR" in out and "找不到" in out or "ERROR:" in out:
        # 任务多半是在 SYSTEM 下注册的，普通用户看不见，
        # 所以看不见不等于没有 —— 看日志里的开机记录来定论
        print("  （这个用户权限看不到任务，问号见下）")
    for line in out.splitlines():
        if re.search(r"任务名|上次运行|上次结果|下次运行|状态|运行方式", line):
            print("  " + line.strip())

    print("\n== 开机自启日志 ==")
    if LOG.exists():
        lines = [l for l in LOG.read_text(encoding="utf-8", errors="replace").splitlines()
                 if l.strip()]
        for l in lines[-12:]:
            print("  " + l)
        boots = [l for l in lines if "开机时间" in l]
        print(f"\n  一共起过 {len(boots)} 次")
    else:
        print("  还没有日志 —— 说明自启脚本一次都没跑过")

    print("\n== 机器上次启动 ==")
    print("  " + ps(["powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"]).strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
