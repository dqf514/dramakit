$ErrorActionPreference = "Continue"
$base = "https://hf-mirror.com/Comfy-Org/MiniMax-H3/resolve/main"
$dest = "E:\ComfyUI\models"

# The 3090 is Ampere: no fp4 tensor cores, so the int8/convrot weights are
# the ones it should use. The text encoder and the video vae get the same
# treatment.
$list = @(
  @("$base/vae/minimax_h3_video_vae_int8_convrot.safetensors",
    "$dest\vae\minimax_h3_video_vae_int8_convrot.safetensors",
    "3090 video vae (int8 convrot)"),
  @("$base/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
    "$dest\text_encoders\qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
    "3090 text encoder (int8 convrot)")
)

foreach ($item in $list) {
  $u = $item[0]
  $p = $item[1]
  $why = $item[2]
  New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
  if (Test-Path $p) {
    $sz = (Get-Item $p).Length
    if ($sz -gt 100000000) {
      Write-Host ("have  " + (Split-Path $p -Leaf) + "  " + [math]::Round($sz / 1gb, 2) + " GB")
      continue
    }
  }
  Write-Host ("get   " + (Split-Path $p -Leaf) + "  <- " + $why)
  $sw = [Diagnostics.Stopwatch]::StartNew()
  curl.exe -L --retry 5 --retry-delay 5 --max-time 7200 -C - -s -o $p $u
  $sw.Stop()
  if (Test-Path $p) {
    Write-Host ("  done " + [math]::Round((Get-Item $p).Length / 1gb, 2) + " GB in " + [math]::Round($sw.Elapsed.TotalSeconds) + "s")
  } else {
    Write-Host "  FAILED"
  }
}
Write-Host "3090 models ready"
