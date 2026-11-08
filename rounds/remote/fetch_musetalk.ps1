$ErrorActionPreference = "Continue"
$root = "E:\musetalk\models"
$dirs = @("musetalk", "musetalkV15", "sd-vae", "whisper", "dwpose", "face-parse-bisent")
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path "$root\$d" | Out-Null }

$files = @(
  @{u="https://hf-mirror.com/TMElyralab/MuseTalk/resolve/main/musetalkV15/unet.pth";      p="$root\musetalkV15\unet.pth"},
  @{u="https://hf-mirror.com/TMElyralab/MuseTalk/resolve/main/musetalkV15/musetalk.json"; p="$root\musetalkV15\musetalk.json"},
  @{u="https://hf-mirror.com/TMElyralab/MuseTalk/resolve/main/musetalk/musetalk.json";   p="$root\musetalk\musetalk.json"},
  @{u="https://hf-mirror.com/stabilityai/sd-vae-ft-mse/resolve/main/config.json";        p="$root\sd-vae\config.json"},
  @{u="https://hf-mirror.com/stabilityai/sd-vae-ft-mse/resolve/main/diffusion_pytorch_model.bin"; p="$root\sd-vae\diffusion_pytorch_model.bin"},
  @{u="https://hf-mirror.com/openai/whisper-tiny/resolve/main/config.json";              p="$root\whisper\config.json"},
  @{u="https://hf-mirror.com/openai/whisper-tiny/resolve/main/pytorch_model.bin";       p="$root\whisper\pytorch_model.bin"},
  @{u="https://hf-mirror.com/openai/whisper-tiny/resolve/main/preprocessor_config.json"; p="$root\whisper\preprocessor_config.json"},
  @{u="https://hf-mirror.com/zllrunning/face-parsing.PyTorch/resolve/main/79999_iter.pth"; p="$root\face-parse-bisent\79999_iter.pth"},
  @{u="https://download.pytorch.org/models/resnet18-5c106cde.pth";                      p="$root\face-parse-bisent\resnet18-5c106cde.pth"},
  @{u="https://hf-mirror.com/yzd-v/DWPose/resolve/main/dw-ll_ucoco_384.pth";            p="$root\dwpose\dw-ll_ucoco_384.pth"}
)

foreach ($f in $files) {
  if (Test-Path $f.p) {
    $sz = (Get-Item $f.p).Length
    if ($sz -gt 100000) { Write-Host ("已有 {0}  {1:N1} MB" -f (Split-Path $f.p -Leaf), ($sz/1mb)); continue }
  }
  Write-Host ("下载 {0} ..." -f (Split-Path $f.p -Leaf))
  curl.exe -L --retry 3 --retry-delay 3 --max-time 1800 -s -o $f.p $f.u
  if (Test-Path $f.p) {
    Write-Host ("  完成 {0:N1} MB" -f ((Get-Item $f.p).Length/1mb))
  } else {
    Write-Host "  失败"
  }
}
Write-Host "全部下载结束"
