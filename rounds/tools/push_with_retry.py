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
    """Can we reach GitHub's door at all?

    The name is not enough: this network resolves github.com to an
    address that does not answer, while other addresses of GitHub's do.
    So the known addresses are tried as well.
    """
    for host in ("github.com",) + GITHUB_IPS:
        try:
            with socket.create_connection((host, 443), timeout=timeout):
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def run(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "超时"


# The ways out, in the order they are tried.  The name github.com is
# resolved by a DNS that hands out an address this network drops, so the
# real addresses of GitHub are tried as well - a request that names one
# of them goes there whatever the name resolves to.
GITHUB_IPS = ("140.82.114.3", "20.205.243.166", "140.82.112.3", "140.82.113.3",
              "140.82.116.3", "20.27.177.113")

# The schannel backend is not what this build of git uses, and the one it
# ships with - openssl - reaches GitHub.  Forcing schannel was making the
# push fail for a reason that had nothing to do with the network.
BASE = ["git", "-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=45",
        "-c", "http.connectTimeout=20"]

ATTEMPTS = [("直连", BASE + ["push", "origin", "main"])]
for _ip in GITHUB_IPS:
    ATTEMPTS.append(("指定地址 " + _ip,
                     BASE + ["-c", "http.curloptResolve=github.com:443:" + _ip,
                             "push", "origin", "main"]))
ATTEMPTS.append(("HTTP/2", BASE + ["-c", "http.version=HTTP/2",
                                   "push", "origin", "main"]))


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
