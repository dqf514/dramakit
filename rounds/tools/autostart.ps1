# Bring the stack up with the machine.
#
# Two things have to be running before a pipeline run can do anything:
# ComfyUI (which makes the pictures and the video) and the DramaKit
# console (which drives it).  Both are started here, detached, so this
# can be run again at any time.
#
# The console is started first, because it is the door a person knocks
# on and it does not need the card.  ComfyUI waits for the driver to be
# awake - at boot the card comes up after the rest of the machine, and
# a ComfyUI that starts too early dies on the first model it loads.
#
# Whatever is already listening on a port is left alone, and a lock
# file keeps two copies from starting at the same time: the boot
# trigger and the logon trigger can both fire, and the second one must
# not fight the first for the port.
#
#   powershell -ExecutionPolicy Bypass -File rounds\tools\autostart.ps1
#   powershell -ExecutionPolicy Bypass -File rounds\tools\autostart.ps1 -Status
#   powershell -ExecutionPolicy Bypass -File rounds\tools\autostart.ps1 -Restart
param(
    [switch]$Status,
    [switch]$Restart
)

$ErrorActionPreference = "Continue"
# so a person running this by hand can read what it says
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$logDir = Join-Path $root "logs\autostart"
$logFile = Join-Path $logDir "autostart.log"
$lockFile = Join-Path $logDir "autostart.lock"

$comfyRoot = "E:\ComfyUI"
$comfyPy = Join-Path $comfyRoot "venv\Scripts\python.exe"
$consoleExe = Join-Path $root "venv\Scripts\dj.exe"

$comfyPort = 8188
$consolePort = 8080

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Say($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    try { Add-Content -Path $logFile -Value $line -Encoding UTF8 } catch {}
    Write-Host $line
}

function PortBusy($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$c
}

function Wait-Http($url, $seconds) {
    $t0 = Get-Date
    while (((Get-Date) - $t0).TotalSeconds -lt $seconds) {
        try {
            $r = Invoke-WebRequest -Uri $url -TimeoutSec 6 -UseBasicParsing
            if ($r.StatusCode -eq 200) { return $true }
        } catch {}
        Start-Sleep -Seconds 2
    }
    return $false
}

function Wait-Path($path, $seconds) {
    $t0 = Get-Date
    while (((Get-Date) - $t0).TotalSeconds -lt $seconds) {
        if (Test-Path $path) { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

# The card comes up after the rest of the machine at boot.  A ComfyUI
# that starts before the driver answers dies on the first model.
function Wait-Gpu($seconds) {
    $t0 = Get-Date
    while (((Get-Date) - $t0).TotalSeconds -lt $seconds) {
        $out = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return $true }
        Start-Sleep -Seconds 5
    }
    return $false
}

function Stop-Listening($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($c) {
        $c | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 3
    }
}

# ----------------------------------------------------------------- status
if ($Status) {
    $c = PortBusy $comfyPort
    $d = PortBusy $consolePort
    Say ("ComfyUI  {0}  ({1})" -f $(if ($c) { "在跑" } else { "没跑" }), $comfyPort)
    Say ("控制台  {0}  ({1})" -f $(if ($d) { "在跑" } else { "没跑" }), $consolePort)
    exit 0
}

Say "==== 开机自启 ===="
# 记下这次是第几次开机起的：机器每次启动都会写一行，
# 回头看日志就知道「开机自启」到底有没有真的触发过。
try {
    $boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
    Say ("  本次开机时间：{0}" -f $boot)
} catch {}

if ($Restart) {
    Say "重启：先把在跑的停掉"
    Stop-Listening $consolePort
    Stop-Listening $comfyPort
}

# ------------------------------------------------------------- the lock
# The boot trigger and the logon trigger can both fire.  The second one
# has to notice the first and go away, not start a second ComfyUI on
# the same port - the second would take the job from the first without
# saying anything.
$held = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $fs = [System.IO.File]::Open($lockFile,
              [System.IO.FileMode]::CreateNew,
              [System.IO.FileAccess]::Write,
              [System.IO.FileShare]::None)
        $fs.Close()
        $held = $true
        break
    } catch {
        # a lock left behind by a run that died is not a lock
        try {
            $age = ((Get-Date) - (Get-Item $lockFile).LastWriteTime).TotalMinutes
            if ($age -gt 15) {
                Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
                continue
            }
        } catch {}
        Start-Sleep -Seconds 3
    }
}
if (-not $held) {
    Say "另一个实例已经在跑了，这里不动手"
    exit 0
}

try {
    # ------------------------------------------------------- the console
    if (PortBusy $consolePort) {
        Say "控制台已经在跑"
    } else {
        if (-not (Wait-Path $consoleExe 120)) {
            Say "**找不到 $consoleExe，控制台起不来**"
        } else {
            Say "起控制台（$consolePort）"
            Start-Process -FilePath $consoleExe `
                -ArgumentList @("serve", "--host", "0.0.0.0", "--port", "$consolePort", "--no-browser") `
                -WorkingDirectory $root -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDir "console.out.log") `
                -RedirectStandardError (Join-Path $logDir "console.err.log") | Out-Null
        }
    }

    # --------------------------------------------------------- ComfyUI
    if (PortBusy $comfyPort) {
        Say "ComfyUI 已经在跑"
    } else {
        if (-not (Wait-Path $comfyPy 120)) {
            Say "**找不到 $comfyPy，ComfyUI 起不来**"
        } else {
            if (Wait-Gpu 300) {
                Say "显卡就绪"
            } else {
                Say "**显卡五分钟没醒，还是先起 ComfyUI**"
            }
            Say "起 ComfyUI（$comfyPort）"
            Start-Process -FilePath $comfyPy `
                -ArgumentList @("main.py", "--listen", "127.0.0.1", "--port", "$comfyPort",
                                "--vram-headroom", "0.5") `
                -WorkingDirectory $comfyRoot -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDir "comfyui.out.log") `
                -RedirectStandardError (Join-Path $logDir "comfyui.err.log") | Out-Null
        }
    }

    # --------------------------------------------------------- waiting
    $okD = Wait-Http "http://127.0.0.1:$consolePort/api/health" 150
    $okC = Wait-Http "http://127.0.0.1:$comfyPort/queue" 180
    Say ("控制台  {0}" -f $(if ($okD) { "起来了" } else { "**没起来**（看 logs\autostart\console.err.log）" }))
    Say ("ComfyUI {0}" -f $(if ($okC) { "起来了" } else { "**没起来**（看 logs\autostart\comfyui.err.log）" }))
}
finally {
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}
