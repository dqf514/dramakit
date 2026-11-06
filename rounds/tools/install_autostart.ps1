# Register the task that brings the stack up with the machine.
#
# The task runs at startup as SYSTEM, so the stack is up before anyone
# sits down at the machine - and again at logon, in case the boot
# trigger fired before the card was awake.  The script itself takes a
# lock, so the two triggers cannot start two ComfyUIs on one port.
#
#   powershell -ExecutionPolicy Bypass -File rounds\tools\install_autostart.ps1
#   powershell -ExecutionPolicy Bypass -File rounds\tools\install_autostart.ps1 -Uninstall
param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$taskName = "DramaKit Stack"
$script = Join-Path $PSScriptRoot "autostart.ps1"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalCheck = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $principalCheck.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "这个脚本要管理员权限，接着会弹一次 UAC，点「是」。"
    $elevatedArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    if ($Uninstall) { $elevatedArgs += "-Uninstall" }
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $elevatedArgs -Wait
    exit 0
}

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "已删掉计划任务「$taskName」"
    exit 0
}

# The task is built with the cmdlets rather than by hand: the XML has
# to be exactly what the scheduler accepts, and it is easier to let
# Windows write it.  The delays are added afterwards, because the
# cmdlets have no way to say "wait a minute, the card is not awake yet".
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory $root

$bootTrigger = New-ScheduledTaskTrigger -AtStartup
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:COMPUTERNAME\$env:USERNAME"

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $taskName -Action $action `
    -Trigger @($bootTrigger, $logonTrigger) -Principal $principal `
    -Settings $settings `
    -Description "开机自动起 DramaKit 控制台和 ComfyUI" -Force | Out-Null

# Now the delays.  The exported XML writes the boot trigger as an empty
# element and the logon trigger without an Enabled line, so the text
# has to be put back the way the schema wants it:
#   <BootTrigger><Enabled>true</Enabled><Delay>PT1M</Delay></BootTrigger>
# and the delay goes before the user on the logon trigger.
$xml = Export-ScheduledTask -TaskName $taskName
# The exported XML writes the boot trigger as an empty element
# (<BootTrigger />), so the whole thing is rewritten rather than
# patched into:
#   <BootTrigger><Enabled>true</Enabled><Delay>PT1M</Delay></BootTrigger>
$xml = [regex]::Replace(
    $xml, '<BootTrigger\s*/>|<BootTrigger>.*?</BootTrigger>',
    '<BootTrigger><Enabled>true</Enabled><Delay>PT1M</Delay></BootTrigger>',
    [System.Text.RegularExpressions.RegexOptions]::Singleline)
# and the delay goes before the user on the logon trigger
if ($xml -notmatch "<LogonTrigger[^>]*>\s*<Delay>") {
    $xml = $xml -replace '(<LogonTrigger>)',
        '$1<Delay>PT2M</Delay>'
}
Register-ScheduledTask -TaskName $taskName -Xml $xml -Force | Out-Null

# and check that it took, rather than believing it did
$check = Export-ScheduledTask -TaskName $taskName
$bootDelay = ([regex]::Match($check, "<BootTrigger>.*?</BootTrigger>", "Singleline")).Value
$logonDelay = ([regex]::Match($check, "<LogonTrigger>.*?</LogonTrigger>", "Singleline")).Value
Write-Host "  开机触发器: $bootDelay"
Write-Host "  登录触发器: $logonDelay"

# A second, independent way in: a shortcut in the folder Windows starts
# with.  The task runs before anyone sits down; this one runs when the
# person arrives.  Both call the same script, and the script leaves
# alone whatever is already listening - so the second one is a safety
# net, not a second set of servers.
$startup = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $startup "DramaKit.lnk"
try {
    $sh = New-Object -ComObject WScript.Shell
    $sc = $sh.CreateShortcut($lnk)
    $sc.TargetPath = "powershell.exe"
    $sc.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
    $sc.WorkingDirectory = $root
    $sc.WindowStyle = 7
    $sc.Description = "开机自动起 DramaKit 控制台和 ComfyUI"
    $sc.Save()
    Write-Host "装好了：启动文件夹也放了一个（$lnk）"
} catch {
    Write-Host "启动文件夹的快捷方式没放成：$($_.Exception.Message)"
}

Write-Host "装好了：计划任务「$taskName」"
Write-Host "  开机后 1 分钟起，登录后 2 分钟再确认一次"
Write-Host "  身份：SYSTEM"
Write-Host "  跑的是：$script"
Write-Host ""
Write-Host "  立刻试一次："
Write-Host "    Start-ScheduledTask -TaskName '$taskName'"
