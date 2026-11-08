$ErrorActionPreference = "Continue"

# The models we want to keep and test, in the order we need them.
#   nvfp4            -> native on the 5080 (Blackwell), smallest
#   int4/int8/convrot -> runs on the 3090 (Ampere has no fp4 tensor cores)
$list = @(
  @("https://hf-mirror.com/Abiray/Minimax-H3-nvfp4-INT4-INT8-Convrot/resolve/main/MiniMax_H3_Ref2VA_pruned_nvfp4.safetensors",
    "E:\ComfyUI\models\diffusion_models\MiniMax_H3_Ref2VA_pruned_nvfp4.safetensors",
    "5080 ref2va (nvfp4)"),
  @("https://hf-mirror.com/Abiray/Minimax-H3-nvfp4-INT4-INT8-Convrot/resolve/main/MiniMax_H3_FL2VA_pruned_nvfp4.safetensors",
    "E:\ComfyUI\models\diffusion_models\MiniMax_H3_FL2VA_pruned_nvfp4.safetensors",
    "5080 fl2va (nvfp4)"),
  @("https://hf-mirror.com/Abiray/Minimax-H3-nvfp4-INT4-INT8-Convrot/resolve/main/MiniMax_H3_Ref2VA_pruned_mixed_int4_int8_convrot.safetensors",
    "E:\ComfyUI\models\diffusion_models\MiniMax_H3_Ref2VA_pruned_mixed_int4_int8_convrot.safetensors",
    "3090 ref2va (int4+int8 convrot)"),
  @("https://hf-mirror.com/Abiray/Minimax-H3-nvfp4-INT4-INT8-Convrot/resolve/main/MiniMax_H3_Ref2VA_pruned_int8_convrot.safetensors",
    "E:\ComfyUI\models\diffusion_models\MiniMax_H3_Ref2VA_pruned_int8_convrot.safetensors",
    "3090 ref2va (int8 convrot)")
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
Write-Host "all downloads done"
Get-ChildItem "E:\ComfyUI\models\diffusion_models" -File | ForEach-Object {
  Write-Host ("  " + [math]::Round($_.Length / 1gb, 2) + " GB  " + $_.Name)
}
