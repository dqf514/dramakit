# The whole thing, once: stop the two services, let the scheduled task
# bring them back, and say how long it took.
#
# The task is a SYSTEM task, so this has to run with the same rights:
#   powershell -ExecutionPolicy Bypass -File rounds\tools\e2e_autostart.ps1
param(
    [string]$Out = ""
)

if (-not $Out) {
    $Out = Join-Path $env:TEMP ("dramakit_e2e_" + [int](Get-Date -Format "HHmmss") + ".txt")
}

function W($m) {
    $line = "{0}" -f $m
    Add-Content -Path $Out -Value $line -Encoding UTF8
}

W "=== 1. 停掉两个服务 ==="
foreach ($p in 8080, 8188) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 5
$left = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in 8080, 8188 }
if ($left) { W ("  还在监听: " + ($left.LocalPort -join ",")) }
else { W "  端口都空了" }

W ""
W "=== 2. 触发计划任务 ==="
Start-ScheduledTask -TaskName "DramaKit Stack"
$t0 = Get-Date
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 3
    $c = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
    $d = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($c -and $d) { break }
}
W ("  用了 " + [int]((Get-Date) - $t0).TotalSeconds + " 秒")
W ("  ComfyUI 8188: " + $(if (Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue) { "在跑" } else { "**没跑**" }))
W ("  控制台 8080:  " + $(if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) { "在跑" } else { "**没跑**" }))
$info = Get-ScheduledTaskInfo -TaskName "DramaKit Stack"
W ("  任务状态: " + (Get-ScheduledTask -TaskName "DramaKit Stack").State)
W ("  上次运行: " + $info.LastRunTime + "  结果=" + $info.LastTaskResult + " (0 = 成功)")

W ""
W "=== 3. 接口真的答话吗 ==="
foreach ($u in @("http://127.0.0.1:8080/api/health", "http://127.0.0.1:8188/queue")) {
    try {
        $r = Invoke-WebRequest $u -TimeoutSec 15 -UseBasicParsing
        W ("  " + $u + " -> HTTP " + $r.StatusCode)
    } catch {
        W ("  " + $u + " -> " + $_.Exception.Message)
    }
}
