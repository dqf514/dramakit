$ErrorActionPreference = "Continue"
$base = "https://hf-mirror.com/openai/whisper-small/resolve/main"
$dest = "E:\musetalk\models\whisper_small"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$names = @("config.json", "generation_config.json", "preprocessor_config.json",
           "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt",
           "model.safetensors")

foreach ($n in $names) {
  $p = "$dest\$n"
  if ((Test-Path $p) -and ((Get-Item $p).Length -gt 1000)) { continue }
  $sw = [Diagnostics.Stopwatch]::StartNew()
  curl.exe -L --retry 4 --retry-delay 3 --max-time 1800 -C - -s -o $p "$base/$n"
  $sw.Stop()
  $sz = if (Test-Path $p) { (Get-Item $p).Length } else { 0 }
  Write-Host ("  " + $n + "  " + [math]::Round($sz / 1mb, 1) + " MB  " + [math]::Round($sw.Elapsed.TotalSeconds) + "s")
}
Write-Host "whisper-small ready"
