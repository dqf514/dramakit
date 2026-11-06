"""A probe: what does the machine see?

The console is started at boot as SYSTEM, and SYSTEM's PATH is the
machine's PATH alone - ffmpeg is in the user's PATH, so everything that
calls ffmpeg comes back "file not found".  The autostart script merges
the user's PATH in before it starts anything; this asks the script
what it ended up with, without starting anything.

    python rounds/tools/check_autostart_env.py
"""
import pathlib
import subprocess
import sys

PS = r"E:\dramakit\rounds\tools\autostart.ps1"
OUT = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\autostart_env.txt")


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    # a task as SYSTEM, calling the script with -Probe
    task = "ZZ_env_probe"
    ps = f'''
$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File "{PS}" -Probe -Out "{OUT}"'
$p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName '{task}' -Action $a -Principal $p -Force | Out-Null
Start-ScheduledTask -TaskName '{task}'
Start-Sleep -Seconds 12
Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false
'''
    wrap = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\env_probe.ps1")
    wrap.write_text(ps, encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(wrap)], check=False)
    # that one needs the rights to register a task, so it is raised
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-Command",
                    "Start-Process powershell -Verb RunAs -ArgumentList "
                    "'-NoProfile -ExecutionPolicy Bypass -File \"%s\"' -Wait" % wrap],
                   check=False)
    if not OUT.exists():
        print("  没拿到输出 —— 探针没跑起来")
        return 1
    for line in OUT.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
