$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$root = "E:\musetalk"
$comfyPy = "E:\ComfyUI\venv\Scripts\python.exe"

# 1) the code
if (-not (Test-Path "$root\scripts\inference.py")) {
    Copy-Item -Recurse -Force "C:\Users\David\AppData\Local\Temp\opencode\MuseTalk" $root
    Write-Host "代码已放到 $root"
}

# 2) a python of its own that still sees the torch that fits this card
if (-not (Test-Path "$root\venv\Scripts\python.exe")) {
    & $comfyPy -m venv --system-site-packages "$root\venv"
    Write-Host "venv 建好"
}

$py = "$root\venv\Scripts\python.exe"
& $py -m pip install --upgrade pip --quiet 2>&1 | Select-Object -Last 2

# 3) only what is missing - torch and transformers come from ComfyUI
& $py -m pip install --quiet "diffusers==0.30.2" omegaconf "librosa>=0.10" soundfile `
    "imageio[ffmpeg]" gdown accelerate 2>&1 | Select-Object -Last 6

Write-Host "--- 自检 ---"
& $py -c @"
import torch, diffusers, transformers, librosa, omegaconf, cv2, sys
print('python', sys.version.split()[0])
print('torch', torch.__version__, 'cuda', torch.cuda.is_available())
print('diffusers', diffusers.__version__, 'transformers', transformers.__version__)
print('librosa', librosa.__version__)
"@
