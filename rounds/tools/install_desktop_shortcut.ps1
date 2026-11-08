# Start the stack by hand, from the desktop.
#
# The stack used to start with the machine, as SYSTEM - and a process
# that runs as SYSTEM cannot be stopped by the person sitting at the
# machine.  Every restart of the console needed an administrator, and
# every "why can this not be stopped" went through a UAC prompt.
#
# So the automatic start is gone and this is what is left: a shortcut on
# the desktop that brings up both - the console and the card that makes
# the pictures - and a way to take them down again.
#
#   Right-click this file -> "Run with PowerShell" as administrator
# (only to remove the scheduled task; the shortcut itself needs nothing)
param(
    [switch]$Uninstall,
    [switch]$Stop
)

$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$script = Join-Path $PSScriptRoot "autostart.ps1"
$taskName = "DramaKit Stack"
$shortcutName = "DramaKit.lnk"
$desktop = [Environment]::GetFolderPath("Desktop")
$startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"

function Say($msg) { Write-Host ("  " + $msg) }

# ------------------------------------------------------------------ #
# 1. the task that started the machine
# ------------------------------------------------------------------ #
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    if ($isAdmin) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        Say "已删掉计划任务「$taskName」（开机不再自动起）"
    } else {
        Write-Host "  计划任务「$taskName」还在，删它要管理员权限。"
        Write-Host "  请右键这个文件 -> 使用 PowerShell 运行（管理员），再跑一次。"
        Write-Host ""
    }
}

# ------------------------------------------------------------------ #
# 2. the shortcut in the startup folder
# ------------------------------------------------------------------ #
$startupLink = Join-Path $startup $shortcutName
if (Test-Path $startupLink) {
    Remove-Item $startupLink -Force -ErrorAction SilentlyContinue
    Say "已删掉开机文件夹里的快捷方式（登录时不再自动起）"
}

# ------------------------------------------------------------------ #
# 3. the shortcut on the desktop
# ------------------------------------------------------------------ #
$desktopLink = Join-Path $desktop "启动 DramaKit（控制台+出图机）.lnk"
if ($Stop) {
    Say "停掉这一套（控制台 8080 与 ComfyUI 8188）"
    foreach ($port in 8080, 8188) {
        $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($c) {
            $c | ForEach-Object {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
                Say ("  停了 " + $port)
            }
        }
    }
    exit 0
}

if (-not (Test-Path $desktopLink)) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($desktopLink)
    $lnk.TargetPath = "powershell.exe"
    $lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
    $lnk.WorkingDirectory = $root
    $lnk.Description = "起 DramaKit 控制台和本地出图机（ComfyUI）"
    $lnk.IconLocation = "$root\venv\Scripts\dj.exe,0"
    $lnk.Save()
    Say "桌面放好了快捷方式：启动 DramaKit（控制台+出图机）"
} else {
    Say "桌面的快捷方式已经在"
}
Say "开机和登录都不再自动起；要的时候双击它，两个一起起来。"
