# The console on 8080 is running as an administrator, and the old one
# keeps the port: a new one starts, cannot bind, and dies, while the old
# one keeps answering with the code from before the change.  So the old
# one has to go first, and this has to be run as an administrator to do
# it.
#
#   powershell -ExecutionPolicy Bypass -File rounds\tools\restart_console_admin.ps1

$ErrorActionPreference = "Continue"
$root = "E:\dramakit"
$consolePort = 8080

# the old console and whatever started it
foreach ($pid in 13064, 31820) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}
# anything else that is holding the port
$c = Get-NetTCPConnection -LocalPort $consolePort -State Listen -ErrorAction SilentlyContinue
if ($c) {
    $c | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 3

$exe = Join-Path $root "venv\Scripts\dj.exe"
Start-Process -FilePath $exe `
    -ArgumentList @("serve", "--host", "0.0.0.0", "--port", "$consolePort", "--no-browser") `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput "E:\dramakit\logs\autostart\console.out.log" `
    -RedirectStandardError "E:\dramakit\logs\autostart\console.err.log" | Out-Null

$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt 90) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$consolePort/api/health" -TimeoutSec 6 -UseBasicParsing
        if ($r.StatusCode -eq 200) { Write-Host "console up"; exit 0 }
    } catch {}
    Start-Sleep -Seconds 2
}
Write-Host "console did not come up"
exit 1
