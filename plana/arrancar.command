#!/usr/bin/env bash
# arrancar.command - Doble clic en el Finder para arrancar el supervisor (abre una ventana de Terminal).
cd "$(dirname "$0")"
PY="$HOME/miniforge3/envs/lerobot/bin/python"

echo "=============================================="
echo "  GARBI · Supervisor"
echo "=============================================="
echo "  1) ACT para el taladro + supervisor   (recomendado)"
echo "  2) Zonas para el taladro + supervisor (sin ACT)"
echo "  3) Supervisor SIN robot (simulado)"
echo "----------------------------------------------"
echo "  En la ventana del supervisor:"
echo "    B = barrer tabla · T = barrer tapete"
echo "    ESPACIO = parada · C = continuar · Z/A = cambiar cerebro · Q = salir"
echo "=============================================="
read -r -p "Elige (1/2/3) [1]: " op
op="${op:-1}"

case "$op" in
  1) ./supervisor_act.sh ;;
  2) "$PY" supervisor.py --real --cerebro zonas ;;
  3) "$PY" supervisor.py --sin-robot --cerebro zonas ;;
  *) echo "Opción no válida" ;;
esac

echo
read -r -p "Supervisor cerrado. Pulsa Intro para cerrar esta ventana..." _
