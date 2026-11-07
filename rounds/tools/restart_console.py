"""Start the console again, and say whether it came up.

The console holds the pipeline in memory, so a change to the code is
not in effect until it is restarted.  This kills what is running, starts
it again, and waits for the door to answer.

Killing by the command line alone is not enough: a console that was
started by the scheduled task has a command line this cannot read, and
it keeps the port - so the new one starts, cannot bind, and dies, while
the old one keeps answering with the code from before the change.  So
the port's owner is killed too.
"""
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = 8080


def _powershell(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(["powershell", "-NoProfile", "-Command", script],
                          capture_output=True, text=True)


def owners() -> list[int]:
    r = _powershell(
        "(Get-NetTCPConnection -LocalPort %d -State Listen -ErrorAction "
        "SilentlyContinue).OwningProcess" % PORT)
    out = []
    for line in (r.stdout or "").split():
        if line.strip().isdigit():
            out.append(int(line.strip()))
    return sorted(set(out))


def kill() -> list[int]:
    _powershell(
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine "
        "-match 'dj.exe serve' } | ForEach-Object { Stop-Process -Id "
        "$_.ProcessId -Force -ErrorAction SilentlyContinue }")
    killed = []
    for pid in owners():
        _powershell("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid)
        killed.append(pid)
    return killed


def up(timeout=90.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/health" % PORT,
                                        timeout=6) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    return False


def main():
    killed = kill()
    time.sleep(3)
    # the console keeps running when this script returns, so its output
    # must not be tied to this one
    subprocess.Popen(
        [r"E:\dramakit\venv\Scripts\python.exe", "-X", "utf8",
         r"E:\dramakit\venv\Scripts\dj.exe", "serve", "--host", "0.0.0.0",
         "--port", str(PORT), "--no-browser"],
        cwd=r"E:\dramakit",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if up():
        now = owners()
        print("控制台起来了（旧的 %s 已杀，端口现在是 %s）"
              % (killed or "没有", now))
        return 0
    print("控制台没起来")
    return 1


if __name__ == "__main__":
    sys.exit(main())
