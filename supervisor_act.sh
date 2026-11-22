#!/usr/bin/env bash
# supervisor_act.sh - Supervisor con el ACT para la APROXIMACIÓN al taladro.
# Todo lo demás lo orquesta el supervisor: detección del morado, seguridad, PARADA (ESPACIO), vuelta a reposo,
# barrido de la tabla (B) y del tapete (T). Con Z / A se cambia en vivo entre ACT y zonas.
#
# Uso:
#   ./supervisor_act.sh                      # modelo por defecto (Xaflas/act_2026-11-21_21-50-02)
#   ./supervisor_act.sh /ruta/a/otro/modelo  # otro modelo (carpeta con config.json y model.safetensors)
#   ./supervisor_act.sh "" --seguir          # modelo por defecto + opciones extra del supervisor
set -euo pipefail
cd "$(dirname "$0")"

REPO="models--Xaflas--act_2026-11-21_21-50-02"
MODELO="${1:-}"
if [[ -z "$MODELO" ]]; then
  MODELO="$(ls -d "$HOME/.cache/huggingface/hub/$REPO/snapshots/"*/ 2>/dev/null | head -1 || true)"
fi
if [[ -z "$MODELO" || ! -f "$MODELO/model.safetensors" ]]; then
  echo "❌ No encuentro el modelo ACT (${MODELO:-$REPO}). Pásalo como primer argumento." >&2
  exit 1
fi

PY="${PYTHON:-$HOME/miniforge3/envs/lerobot/bin/python}"
echo "Modelo ACT: $MODELO"
exec "$PY" supervisor.py --real --cerebro act --modelo "$MODELO" "${@:2}"
