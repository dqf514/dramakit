"""Keep trying to push until the network lets it through.

GitHub answers from this machine now and then: the connection is
accepted and then reset, or it times out. The work is committed
locally either way - what is missing is only the trip to the other
side - so the push is simply retried until it goes through.

Git retries by itself and each try takes minutes, which is far too
slow for a link that comes and goes in seconds. So the door is tried
first, with a short timeout, and git is only asked to push when the
door is already open.

It says what it did every time, so there is a record of how long the
network was down and of the moment it came back.
"""
import socket
import subprocess
import time
from pathlib import Path

REPO = Path(r"E:\dramakit")
LOG = Path(r"C:\Users\David\AppData\Local\Temp\opencode\git_push.log")
DEADLINE = time.time() + 12 * 3600


def note(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def door_open(timeout=5.0):
    """Can we reach GitHub's door at all?"""
    try:
        with socket.create_connection(("github.com", 443), timeout=timeout):
            return True
    except Exception:  # noqa: BLE001
        return False


def run(cmd, timeout=240):
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "超时"


note("=== 开始推送（网络时通时断就一直试）===")
tries = 0
closed = 0
ok = False
while time.time() < DEADLINE and not ok:
    tries += 1
    if not door_open():
        closed += 1
        if closed % 12 == 1:
            note("门关着（第 %d 次探，第 %d 次关）" % (tries, closed))
        time.sleep(8)
        continue
    # Three ways out, tried in turn:
#   - straight out, the way the machine normally reaches the internet
#   - straight out but to a named address of GitHub's, for when the name
#     resolves to one that this network drops
#   - through the proxy, for when the proxy is working
# The ssl backend this build has is the one that works: the system
# config asks for openssl, which this build does not have, and that
# only shows up once a connection is made.
    attempts = [
        ["git", "-c", "http.sslBackend=schannel", "push", "origin", "main"],
        ["git", "-c", "http.sslBackend=schannel",
         "-c", "http.curloptResolve=github.com:443:20.205.243.166",
         "push", "origin", "main"],
        ["git", "-c", "http.sslBackend=schannel",
         "-c", "http.proxy=http://127.0.0.1:7897", "push", "origin", "main"],
    ]
    code, out = 1, ""
    for cmd in attempts:
        code, out = run(cmd)
        if code == 0:
            break
    clean = "\n".join(l for l in out.split("\n")
                      if "LF will be replaced" not in l).strip()
    if code == 0 and ("Everything up-to-date" in clean or "-> main" in clean):
        note("✓ 第 %d 次：推上去了" % tries)
        for line in clean.split("\n"):
            if line.strip():
                note("   " + line.strip())
        ok = True
        break
    err = next((l for l in clean.split("\n") if "fatal" in l or "error" in l), clean[:120])
    note("第 %d 次失败：%s" % (tries, err.strip()[:160]))
    time.sleep(10)

if not ok:
    note("=== 12 小时都没推上去，放弃 ===")
    raise SystemExit(1)

code, out = run(["git", "rev-list", "--left-right", "--count",
                 "origin/main...HEAD"])
note("远端与本地的差距（远端独有 / 本地独有）：" + out.strip())
note("=== 结束 ===")
