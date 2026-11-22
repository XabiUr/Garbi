#!/usr/bin/env bash
# Visor 3D de Garbi en Linux o macOS: trae lo último de GitHub y abre el visor de MuJoCo.
set -euo pipefail
cd "$(dirname "$0")/.."
RAMA=claude/vigilant-franklin-xjlncg
git fetch origin "$RAMA" && git checkout "$RAMA" && git pull --ff-only origin "$RAMA"
if [ ! -x .venv-visor/bin/python ]; then
  python3 -m venv .venv-visor
  .venv-visor/bin/python -m pip install mujoco numpy opencv-python pillow
fi
if [ "$(uname)" = "Darwin" ]; then
  .venv-visor/bin/mjpython -m garbi.ver  # en macOS el visor pasivo necesita mjpython
else
  .venv-visor/bin/python -m garbi.ver
fi
