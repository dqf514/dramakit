# Bring the local stack back up.
#
# Two things have to be running before a pipeline run can do anything:
# ComfyUI (which makes the pictures and the video) and the DramaKit
# console (which drives them). Both are started detached, so this can be
# run again at any time - it stops what is already there first, because
# a second ComfyUI on the same port would silently take over the job
# from the first one.
#
#   powershell -ExecutionPolicy Bypass -File rounds\tools\start_local_stack.ps1
#
param(
    [switch]$NoResume
)

$ErrorActionPreference = "Continue"
$root = "E:\dramakit"

function Stop-Listening($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($c) {
        $c | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
    }
}

Write-Host "== 停掉旧的 =="
Stop-Listening 8080
Stop-Listening 8188
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*main.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3

Write-Host "== 起 ComfyUI =="
# --vram-headroom is in GB. The H3 text encoder is 14.61GB and this card
# has 16GB, so 1.5GB of headroom pushes the encoder onto the CPU and
# every clip gets minutes slower.
Start-Process -FilePath "E:\ComfyUI\venv\Scripts\python.exe" `
    -ArgumentList "main.py", "--listen", "127.0.0.1", "--port", "8188",
                  "--vram-headroom", "0.5" `
    -WorkingDirectory "E:\ComfyUI" -WindowStyle Hidden

Write-Host "== 起 DramaKit 控制台 =="
Start-Process -FilePath "$root\venv\Scripts\dj.exe" `
    -ArgumentList "serve", "--host", "0.0.0.0", "--port", "8080", "--no-browser" `
    -WorkingDirectory $root -WindowStyle Hidden

# wait for both to answer before saying anything is up
$okC = $false
$okD = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 3
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8188/queue" -TimeoutSec 8 -UseBasicParsing | Out-Null
        $okC = $true
    } catch {}
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/jobs" -TimeoutSec 8 -UseBasicParsing | Out-Null
        $okD = $true
    } catch {}
    if ($okC -and $okD) { break }
}
Write-Host "  ComfyUI: $(if($okC){'起来了'}else{'**没起来**'})"
Write-Host "  控制台:  $(if($okD){'起来了'}else{'**没起来**'})"

if ($okD -and -not $NoResume) {
    Write-Host "== 续跑最近的流水线 =="
    try {
        $body = @{ project = "星际骷髅兵"; chapters = @(1) } | ConvertTo-Json
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/resume" -Method Post `
            -Body $body -ContentType "application/json" -TimeoutSec 90
        Write-Host "  任务 $($r.job)"
    } catch {
        Write-Host "  续跑失败: $($_.Exception.Message)"
    }
}
