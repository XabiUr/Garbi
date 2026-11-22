#!/usr/bin/env bash
# arrancar.command - Doble clic en el Finder para arrancar el supervisor (abre una ventana de Terminal).
cd "$(dirname "$0")"
PLANA="$(pwd)"
PY="$HOME/miniforge3/envs/lerobot/bin/python"

echo "=============================================="
echo "  GARBI · Supervisor"
echo "=============================================="
echo "  1) ACT para el taladro + supervisor   (recomendado)"
echo "  2) Zonas para el taladro + supervisor (sin ACT)"
echo "  3) Supervisor SIN robot (simulado)"
echo "  4) WEB + supervisor  (botones: encender, limpiar tabla/tapete, parar y elegir ACT/Zonas)"
echo "----------------------------------------------"
echo "  En la ventana del supervisor:"
echo "    B = barrer tabla · T = barrer tapete"
echo "    ESPACIO = parada · C = continuar · Z/A = cambiar cerebro · Q = salir"
echo "=============================================="
read -r -p "Elige (1-4) [1]: " op
op="${op:-1}"

case "$op" in
  1) ./supervisor_act.sh ;;
  2) "$PY" supervisor.py --real --cerebro zonas ;;
  3) "$PY" supervisor.py --sin-robot --cerebro zonas ;;
  4)
    if lsof -nP -iTCP:8800 -sTCP:LISTEN >/dev/null 2>&1; then
      echo "La web ya está abierta (de antes): la abro en el navegador. Para cerrarla, Ctrl+C en su Terminal."
      open "http://localhost:8800/"
      exit 0
    fi
    WEB="$(cd ../Robotalde_1-claude-vigilant-franklin-xjlncg && pwd)"
    # El supervisor carga los DOS cerebros (si hay modelo ACT) y arranca con ACT; desde la web se cambia.
    MODELO="$(ls -d "$HOME/.cache/huggingface/hub/models--Xaflas--act_2026-11-21_21-50-02/snapshots/"*/ 2>/dev/null | head -1)"
    if [[ -n "$MODELO" ]]; then
      ARGS="--real --cerebro act --modelo $MODELO"
    else
      echo "⚠️  No encuentro el modelo ACT: solo zonas"
      ARGS="--real --cerebro zonas"
    fi
    echo "Abriendo la web: pulsa ENCENDER para arrancar el supervisor"
    (cd "$WEB" && "$PY" -m garbi.producto.app --supervisor --supervisor-dir "$PLANA" --supervisor-args "$ARGS")
    ;;
  *) echo "Opción no válida" ;;
esac

echo
read -r -p "Supervisor cerrado. Pulsa Intro para cerrar esta ventana..." _
