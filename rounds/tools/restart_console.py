"""Start the console again, and say whether it came up.

The console holds the pipeline in memory, so a change to the code is
not in effect until it is restarted.  This kills what is running, starts
it again, and waits for the door to answer.
"""
import subprocess
import sys
import time
import urllib.error
import urllib.request

KILL = ("powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine "
        "-match 'dj.exe serve' } | ForEach-Object { Stop-Process -Id "
        "$_.ProcessId -Force -ErrorAction SilentlyContinue }")


def alive():
    r = subprocess.run(KILL, capture_output=True, text=True)
    return r


def up(timeout=90.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/api/health",
                                        timeout=6) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    return False


def main():
    alive()
    time.sleep(3)
    subprocess.Popen(
        [r"E:\dramakit\venv\Scripts\python.exe", "-X", "utf8",
         r"E:\dramakit\venv\Scripts\dj.exe", "serve", "--host", "0.0.0.0",
         "--port", "8080", "--no-browser"],
        cwd=r"E:\dramakit")
    if up():
        print("控制台起来了")
        return 0
    print("控制台没起来")
    return 1


if __name__ == "__main__":
    sys.exit(main())
