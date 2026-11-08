# Restart the console with the new code.
#
# The console on 8080 is running as an administrator, and the code it
# loaded at 14:40 is still the code it is running - a new console
# cannot take the port while the old one holds it, so the new one dies
# and the old one keeps answering with the old code.  Only an
# administrator can stop the old one.
#
#   Right-click this file -> "Run with PowerShell" as administrator
# or, from an administrator PowerShell:
#   powershell -ExecutionPolicy Bypass -File E:\dramakit\rounds\tools\restart_console_admin.ps1
#
# Only the console is touched.  The ComfyUI on 8188 (the local card)
# keeps running - it is the thing that makes the pictures, and it is
# not what is out of date.
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
    Write-Host "这个脚本要管理员权限。"
    Write-Host "请右键这个文件 -> 使用 PowerShell 运行（管理员），或者在管理员 PowerShell 里再跑一次。"
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

# 2. the new one
Say "起新的控制台……"
Start-Process -FilePath $exe `
    -ArgumentList @("serve", "--host", "0.0.0.0", "--port", "$port", "--no-browser") `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "console.out.log") `
    -RedirectStandardError (Join-Path $logDir "console.err.log") | Out-Null

# 3. is it up, and is it the new code?
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/skills" -TimeoutSec 6
        if ($r.ok) { $ok = $true; break }
    } catch {}
}
if (-not $ok) {
    Say "控制台没起来。看 logs\autostart\console.err.log"
    exit 1
}
Say "控制台起来了：http://127.0.0.1:$port/"
# the type column is in the new code and not in the old: if it is here,
# the new code is the one that is running
$hasGenre = ($r.selection.PSObject.Properties.Name -contains "genre")
if ($hasGenre) {
    Say "新代码已经在跑（技能面板里「类型」栏）"
} else {
    Say "**还是旧代码**：技能面板里没有「类型」栏"
    exit 1
}
Write-Host ""
Write-Host "  刷新浏览器（Ctrl+F5）就能看到新的技能面板和六步流程。"
Write-Host ""
Start-Sleep -Seconds 8
