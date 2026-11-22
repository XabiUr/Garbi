#!/usr/bin/env bash
# Prepara el entorno de simulación de LeWelder (Linux). En Windows: mismos pasos con PowerShell.
set -euo pipefail
cd "$(dirname "$0")"
uv venv --python 3.12 .venv
# PyTorch: CPU en la nube; en un PC con NVIDIA, quitar --index-url para la versión con CUDA.
uv pip install --python .venv torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv -e ".[dev]"
echo "Listo. Activa con: source .venv/bin/activate  (render sin pantalla: export MUJOCO_GL=egl)"
