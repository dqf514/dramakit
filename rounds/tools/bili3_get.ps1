$ErrorActionPreference = "Continue"
$dir = "C:\tmp\bili3"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$urls = & "E:\dramakit\venv\Scripts\python.exe" "E:\dramakit\rounds\tools\bili_info.py" BV1b9HA6JEzv 3 4 6 10 11
foreach ($line in $urls) {
  if (-not $line) { continue }
  $parts = $line -split "`t"
  if ($parts.Count -lt 4) { continue }
  $pid_ = $parts[0]
  $out = "$dir\p$pid_.mp4"
  if ((Test-Path $out) -and (Get-Item $out).Length -gt 1000000) {
    Write-Host ("have p$pid_ " + [math]::Round((Get-Item $out).Length/1mb,1) + " MB")
    continue
  }
  Write-Host ("get p$pid_ ...")
  curl.exe -L --retry 3 --max-time 1800 -s -o $out `
    -H "User-Agent: Mozilla/5.0" `
    -H "Referer: https://www.bilibili.com/video/BV1b9HA6JEzv/?p=$pid_" $parts[3]
  if (Test-Path $out) {
    Write-Host ("  done " + [math]::Round((Get-Item $out).Length/1mb,1) + " MB")
  }
}
Write-Host "all done"
Get-ChildItem $dir -Filter *.mp4 | ForEach-Object { Write-Host ("  " + $_.Name + "  " + [math]::Round($_.Length/1mb,1) + " MB") }
