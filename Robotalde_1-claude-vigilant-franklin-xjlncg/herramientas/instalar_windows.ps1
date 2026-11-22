# Garbi · instalación en Windows (portátil del hackathon), desde cero.
#
# Uso (PowerShell, en la carpeta del repositorio ya clonado):
#     powershell -ExecutionPolicy Bypass -File herramientas\instalar_windows.ps1
#
# Qué hace:
#   1. Instala uv (gestor de Python) si falta, y ffmpeg con winget si falta.
#   2. Crea .venv con Python 3.12.
#   3. PyTorch con CUDA si hay NVIDIA (nvidia-smi); si no, el de CPU.
#   4. El proyecto (LeRobot 0.7, MuJoCo, OpenCV...) y MediaPipe para las manos, con su modelo en calib/.
#   5. Una prueba rápida (tests sin hardware).
# Se puede repetir sin miedo: lo que ya está, lo salta.

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
function Paso($t) { Write-Host "`n== $t" -ForegroundColor Cyan }

Paso "1/5 uv y ffmpeg"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
uv --version
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
        Write-Host "ffmpeg instalado: CIERRA y vuelve a abrir PowerShell al terminar para que se vea." -ForegroundColor Yellow
    } else {
        Write-Host "Sin winget: instala ffmpeg a mano (https://www.gyan.dev/ffmpeg/builds/) si falla grabar vídeo." -ForegroundColor Yellow
    }
}

Paso "2/5 entorno .venv con Python 3.12"
if (-not (Test-Path ".venv\Scripts\python.exe")) { uv venv --python 3.12 .venv }
$py = Join-Path $raiz ".venv\Scripts\python.exe"
$env:VIRTUAL_ENV = Join-Path $raiz ".venv"

Paso "3/5 PyTorch"
$nvidia = $null -ne (Get-Command nvidia-smi -ErrorAction SilentlyContinue)
if ($nvidia) {
    Write-Host "NVIDIA detectada: PyTorch con CUDA 12.4"
    uv pip install --python $py torch torchvision --index-url https://download.pytorch.org/whl/cu124
} else {
    Write-Host "Sin NVIDIA: PyTorch de CPU (entrenar se hace en HF Jobs; ejecutar ACT en CPU va sobrado)"
    uv pip install --python $py torch torchvision --index-url https://download.pytorch.org/whl/cpu
}

Paso "4/5 Proyecto (LeRobot 0.7, MuJoCo, OpenCV, MediaPipe)"
uv pip install --python $py -e ".[dev,manos]"
# Que no quede la versión sin ventanas de OpenCV (rompe las herramientas con ventana)
uv pip uninstall --python $py opencv-python-headless 2>$null
New-Item -ItemType Directory -Force -Path calib | Out-Null
if (-not (Test-Path "calib\hand_landmarker.task")) {
    Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task" -OutFile "calib\hand_landmarker.task"
}

Paso "5/5 Prueba rápida (sin hardware)"
$env:MUJOCO_GL = "glfw"
& $py -m pytest -q tests/test_garbi_real.py tests/test_garbi_herramientas.py
if ($LASTEXITCODE -ne 0) { Write-Host "Algún test ha fallado: copia el error al Claude Code local." -ForegroundColor Yellow }

Write-Host "`nListo. Para trabajar:" -ForegroundColor Green
Write-Host "   .venv\Scripts\activate"
Write-Host "   hf auth login                       (token de Hugging Face con permiso de escritura)"
Write-Host "   lerobot-find-port                   (puertos de los brazos)"
Write-Host "   python -m garbi.ver                 (simulación 3D, para ver que todo carga)"
Write-Host "   Guía: docs\garbi-guia-hackathon.md  ·  Acompañante: abre 'claude' aquí y escribe /garbi-sitio"
