#!/usr/bin/env bash
# Script de arranque del entorno de nube (Tobotalde_1). Se ejecuta desde la carpeta que contiene Robotalde_1.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Solo lo necesario para renderizar sin pantalla (el vídeo lo escribe OpenCV: ffmpeg no hace falta y tarda mucho)
apt-get update -qq && apt-get install -y -qq --no-install-recommends libosmesa6 libegl1 libgl1 libglfw3
if ! command -v arduino-cli >/dev/null; then
  curl -fsSL -o /tmp/acli.tgz https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Linux_64bit.tar.gz
  tar xzf /tmp/acli.tgz -C /usr/local/bin arduino-cli
fi
arduino-cli config init --overwrite >/dev/null
arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index >/dev/null
arduino-cli core install arduino:avr esp32:esp32 >/dev/null
arduino-cli lib install "Adafruit BNO055" "MPU6050_light" >/dev/null
if [ -d Robotalde_1 ]; then
  cd Robotalde_1
  uv venv --allow-existing --python 3.12 .venv
  uv pip install --python .venv -q torch torchvision --index-url https://download.pytorch.org/whl/cpu
  uv pip install --python .venv -q -e ".[dev]"
fi
