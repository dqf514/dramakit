$ErrorActionPreference = "Continue"
$base = "https://hf-mirror.com/Comfy-Org/MiniMax-H3/resolve/main"
$dest = "E:\ComfyUI\models"

$list = @(
  @("$base/diffusion_models/minimax_h3_ref2va_pruned_w6a8.safetensors", "$dest\diffusion_models\minimax_h3_ref2va_pruned_w6a8.safetensors"),
  @("$base/loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors", "$dest\loras\minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors")
)

foreach ($item in $list) {
  $u = $item[0]
  $p = $item[1]
  New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
  if (Test-Path $p) {
    $sz = (Get-Item $p).Length
    if ($sz -gt 100000000) {
      Write-Host ("have " + (Split-Path $p -Leaf) + "  " + [math]::Round($sz / 1gb, 2) + " GB")
      continue
    }
  }
  Write-Host ("downloading " + (Split-Path $p -Leaf))
  $sw = [Diagnostics.Stopwatch]::StartNew()
  curl.exe -L --retry 5 --retry-delay 5 --max-time 7200 -C - -s -o $p $u
  $sw.Stop()
  if (Test-Path $p) {
    Write-Host ("  done " + [math]::Round((Get-Item $p).Length / 1gb, 2) + " GB in " + [math]::Round($sw.Elapsed.TotalSeconds) + "s")
  } else {
    Write-Host "  failed"
  }
}
Write-Host "ref2va weights done"
