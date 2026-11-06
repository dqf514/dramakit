# What does the machine itself see?
#
# The console is started at boot as SYSTEM, so whatever SYSTEM can find
# is what the console can find.  This asks exactly that: the PATH, and
# whether ffmpeg - the thing the voice samples are made with - is in
# it.
#
#   powershell -ExecutionPolicy Bypass -File rounds\tools\check_system_path.ps1
param(
    [string]$Out = "C:\Users\David\AppData\Local\Temp\opencode\system_path.txt"
)

$lines = @()
$lines += "跑的人: " + [Security.Principal.WindowsIdentity]::GetCurrent().Name
$lines += "PATH 条数: " + (@($env:PATH -split ';') | Where-Object { $_ }).Count
$lines += "PATH 里有 WinGet: " + ($env:PATH -match "WinGet")
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
$lines += "ffmpeg: " + $(if ($ff) { $ff.Source } else { "**找不到**" })
if ($ff) {
    $v = (& ffmpeg -version 2>&1 | Select-Object -First 1)
    $lines += "版本: $v"
}
$lines += "--- PATH ---"
$lines += ($env:PATH -split ';')
Set-Content -Path $Out -Value ($lines -join "`r`n") -Encoding UTF8
Write-Host ($lines -join "`n")
