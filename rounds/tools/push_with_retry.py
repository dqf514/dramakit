"""Keep trying to push until the network lets it through.

GitHub answers from this machine now and then: the connection is
accepted and then reset, or it times out. The work is committed
locally either way - what is missing is only the trip to the other
side - so the push is simply retried until it goes through.

Two things were wrong with the first version of this. It forced the
schannel backend, which this build of git does not have working
(the one it ships with, openssl, reaches GitHub fine) - and it left
the push to hang for minutes when the connection stalls halfway
through the upload, which is exactly when the link is at its worst.

So: the door is tried first with a short timeout, and the push itself
is given a short leash. Every way out is tried in turn, and each one
is written down, so there is a record of what the network was doing.

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


def run(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "超时"


# The ways out, in the order they are tried.  The first one is the plain
# push with the backend this git was built with - openssl, which reaches
# GitHub.  The second asks for HTTP/2, for when the link drops a
# half-finished HTTP/1.1 upload.  The third names one of GitHub's own
# addresses, for when the name resolves to one this network drops.  The
# last goes through the proxy, for when the proxy is working.
ATTEMPTS = [
    ("直连", ["git", "push", "origin", "main"]),
    ("HTTP/2", ["git", "-c", "http.version=HTTP/2", "push", "origin", "main"]),
    ("指定地址", ["git", "-c", "http.curloptResolve=github.com:443:20.205.243.166",
                  "push", "origin", "main"]),
    ("走代理", ["git", "-c", "http.proxy=http://127.0.0.1:7897",
                "push", "origin", "main"]),
]


def pushed(out: str) -> bool:
    """Did the push land?"""
    clean = "\n".join(l for l in out.split("\n")
                      if "LF will be replaced" not in l).strip()
    return ("Everything up-to-date" in clean or "-> main" in clean
            or "main -> main" in clean)


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
    for label, cmd in ATTEMPTS:
        code, out = run(cmd)
        if code == 0 and pushed(out):
            note("✓ 第 %d 次（%s）：推上去了" % (tries, label))
            for line in out.split("\n"):
                if line.strip() and "LF will be replaced" not in line:
                    note("   " + line.strip()[:160])
            ok = True
            break
        err = next((l for l in out.split("\n")
                    if "fatal" in l or "error" in l), out.strip()[:120])
        note("  第 %d 次（%s）失败：%s" % (tries, label, err.strip()[:150]))
        if code == 124:
            break
    if ok:
        break
    time.sleep(10)

if not ok:
    note("=== 12 小时都没推上去，放弃 ===")
    raise SystemExit(1)

code, out = run(["git", "rev-list", "--left-right", "--count",
                 "origin/main...HEAD"])
note("远端与本地的差距（远端独有 / 本地独有）：" + out.strip())
note("=== 结束 ===")
