# Wait for the clip that is being made now, then bring the console back up
# with the two cards in the pool and carry the run on.
#
# The console builds its pool when a run starts, so the card that was
# added tonight is not in the running one.  The run is carried on with
# the plan it had: the same chapters, the same episodes, the same
# stages, and the stages that are done are skipped.
#
#   powershell -ExecutionPolicy Bypass -File rounds\tools\wait_then_resume.ps1
param(
    [string]$Project = "穿成亿万总裁他前妻",
    [string]$Card = "http://192.168.31.8:8188",
    [int]$MaxWaitMinutes = 40,
    [string]$Log = "E:\dramakit\logs\autostart\resume.log"
)

$ErrorActionPreference = "Continue"
function Say($m) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m
    try { Add-Content -Path $Log -Value $line -Encoding UTF8 } catch {}
}

Say "=== 等当前这一段视频做完 ==="

$done = $false
$t0 = Get-Date
while (((Get-Date) - $t0).TotalMinutes -lt $MaxWaitMinutes) {
    Start-Sleep -Seconds 30
    try {
        $q = Invoke-RestMethod -Uri "$Card/queue" -TimeoutSec 12
        $running = @($q.queue_running).Count
        if ($running -eq 0) { $done = $true; break }
        Say ("  卡上还跑着 {0} 段" -f $running)
    } catch {
        Say ("  问不到卡了：{0}" -f $_.Exception.Message)
    }
}
if (-not $done) { Say "等了太久，不动了（这一轮继续用一张卡）"; exit 0 }
Say "这一段做完了"

Say "=== 重启控制台 ==="
foreach ($p in 8080, 8188) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 6
Start-ScheduledTask -TaskName "DramaKit Stack"

$up = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 3
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/health" -TimeoutSec 8
        if ($h.ok) { $up = $true; break }
    } catch {}
}
if (-not $up) { Say "控制台没起来"; exit 1 }
Say "控制台起来了"

Say "=== 续跑 ==="
$body = @{ project = $Project } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/resume" -Method Post `
        -Body $body -ContentType "application/json" -TimeoutSec 90
    Say ("  续跑任务 {0}" -f $r.job)
} catch {
    Say ("  续跑失败：{0}" -f $_.Exception.Message)
    exit 1
}

Say "=== 节点池 ==="
try {
    $nodes = Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/nodes" -TimeoutSec 30
    foreach ($n in $nodes.nodes) {
        Say ("  {0,-12} {1,-26} 在线={2}" -f $n.name, $n.base_url, $n.online)
    }
} catch {
    Say ("  节点读不出来：{0}" -f $_.Exception.Message)
}
Say "=== 结束 ==="
