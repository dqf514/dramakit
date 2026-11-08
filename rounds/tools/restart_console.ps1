# Restart the console with the new code.
#
# The console on 8080 was started by the scheduled task as SYSTEM, so
# only an administrator can stop it - and it holds the code it loaded
# when it started, so a new console cannot take the port while the old
# one holds it.  A new console would die and the old one would keep
# answering with the old code.
#
#   Right-click this file -> "Run with PowerShell" as administrator
# or, from an administrator PowerShell:
#   powershell -ExecutionPolicy Bypass -File E:\dramakit\rounds\tools\restart_console.ps1
#
# Only the console is touched.  The ComfyUI on 8188 (the local card)
# keeps running - it makes the pictures, it is not what changed.
param()

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$root = "E:\dramakit"
$port = 8080
$exe = Join-Path $root "venv\Scripts\dj.exe"
$logDir = Join-Path $root "logs\autostart"

function Say($msg) {
    Write-Host ("  " + $msg)
}

$me = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = (New-Object Security.Principal.WindowsPrincipal($me)).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "这个脚本要管理员权限（控制台是以 SYSTEM 身份跑的）。"
    Write-Host "请右键这个文件 -> 使用 PowerShell 运行（管理员）。"
    exit 1
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# 1. the console that holds the port
$owners = @()
$c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($c) { $owners = @($c.OwningProcess | Select-Object -Unique) }
foreach ($pid_ in $owners) {
    Say "结束占着 $port 的旧控制台（pid=$pid_）"
    Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
}
# and any other copy of it, wherever it was started from
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "dj\.exe" -and $_.CommandLine -match "serve" } |
    ForEach-Object {
        Say "结束另一个控制台（pid=$($_.ProcessId)）"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 3

# 2. the PATH the tools are in: ffmpeg lives in the user's PATH, and
# without it the voice samples and the length checks come back
# "file not found"
$envFile = Join-Path $root "rounds\tools\autostart_env.json"
if (Test-Path $envFile) {
    try {
        $uenv = Get-Content $envFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($uenv.path) {
            $parts = @($env:PATH -split ';') + @($uenv.path -split ';')
            $seen = @{}
            $merged = @()
            foreach ($p in $parts) {
                if (-not $p) { continue }
                $k = $p.TrimEnd('\').ToLower()
                if ($seen.ContainsKey($k)) { continue }
                $seen[$k] = $true
                $merged += $p
            }
            $env:PATH = ($merged -join ';')
            Say ("把用户的 PATH 合进来了（{0} 条）" -f $merged.Count)
        }
    } catch {
        Say ("用户的 PATH 没合进来：{0}" -f $_.Exception.Message)
    }
}

# 3. the new one
Say "起新的控制台……"
Start-Process -FilePath $exe `
    -ArgumentList @("serve", "--host", "0.0.0.0", "--port", "$port", "--no-browser") `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "console.out.log") `
    -RedirectStandardError (Join-Path $logDir "console.err.log") | Out-Null

# 4. is it up, and is it the new code?
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/state" -TimeoutSec 6
        if ($r.ok) { $ok = $true; break }
    } catch {}
}
if (-not $ok) {
    Say "控制台没起来。看 logs\autostart\console.err.log"
    exit 1
}
Say "控制台起来了：http://127.0.0.1:$port/"
# The stage list comes from the pipeline now: if it is here, the console
# is running the new code.
$hasStages = ($r.PSObject.Properties.Name -contains "stages")
if ($hasStages) {
    Say "新代码已经在跑（运行状态里的阶段列表是管线自己的顺序）"
} else {
    Say "**还是旧代码**：运行状态里的阶段列表不是管线自己的"
    exit 1
}
Write-Host ""
Write-Host "  刷新浏览器（Ctrl+F5）就能看到新的东西。"
Write-Host ""
Start-Sleep -Seconds 5
