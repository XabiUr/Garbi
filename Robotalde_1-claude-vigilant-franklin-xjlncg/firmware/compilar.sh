#!/usr/bin/env bash
# Compila los dos firmwares para Arduino Nano y ESP32 (y el del alumno con cada opción de IMU) con arduino-cli.
# Uso: firmware/compilar.sh            (necesita los núcleos arduino:avr y esp32:esp32 y las librerías
#                                        "Adafruit BNO055" y "MPU6050_light")
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SALIDA="${TMPDIR:-/tmp}/lewelder-firmware"
PLACAS=("arduino:avr:nano" "esp32:esp32:esp32")
fallos=0

compilar() {  # compilar <boceto> <placa> <opción de IMU o vacío>
  local boceto=$1 placa=$2 imu=$3
  local nombre="$boceto · $placa${imu:+ · $imu}"
  local args=(compile --fqbn "$placa" --build-path "$SALIDA/$boceto-${placa//:/_}-${imu:-defecto}")
  [[ -n $imu ]] && args+=(--build-property "compiler.cpp.extra_flags=-D$imu")
  echo "== $nombre"
  if salida=$(arduino-cli "${args[@]}" "$DIR/$boceto" 2>&1); then
    grep -E "^(Sketch uses|Global variables|El sketch usa|Las variables Globales)" <<<"$salida" || true
  else
    echo "$salida"
    echo "!! FALLO: $nombre"
    fallos=$((fallos + 1))
  fi
}

for placa in "${PLACAS[@]}"; do
  for imu in IMU_BNO055 IMU_MPU6050 SIN_IMU; do
    compilar antorcha_alumno "$placa" "$imu"
  done
  compilar antorcha_robot "$placa" ""
done

if ((fallos)); then
  echo "$fallos compilaciones fallidas"
  exit 1
fi
echo "Todo compilado."
