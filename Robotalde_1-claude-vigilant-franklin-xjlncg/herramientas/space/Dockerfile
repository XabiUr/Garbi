# LeWelder · simulador de la demo como Hugging Face Space (Docker).
# Se construye desde la RAÍZ del repositorio:
#     docker build -f herramientas/space/Dockerfile -t lewelder-sim .
#     docker run --rm -p 7860:7860 lewelder-sim          # → http://localhost:7860/
# Para subirlo al Space: copiar este Dockerfile y el README.md de esta carpeta a la raíz del repo del Space, junto con
# las carpetas que se copian abajo (ver README.md).
FROM python:3.12-slim

# Sin GPU: MuJoCo solo integra la física (no se renderizan cámaras en el bucle). OSMesa por si una política
# entrenada pide imágenes (MUJOCO_GL=osmesa), y libgl para que MuJoCo cargue.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libosmesa6 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face ejecuta el contenedor con el usuario 1000.
RUN useradd -m -u 1000 usuario
WORKDIR /app

COPY herramientas/space/requirements-space.txt /app/requirements-space.txt
RUN pip install --no-cache-dir -r /app/requirements-space.txt

COPY --chown=usuario lewelder /app/lewelder
COPY --chown=usuario sim /app/sim
COPY --chown=usuario web /app/web
COPY --chown=usuario assets/so101 /app/assets/so101
COPY --chown=usuario hardware/v2/cad/stl /app/hardware/v2/cad/stl
RUN mkdir -p /app/salidas && chown -R usuario /app

USER usuario
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    MUJOCO_GL=osmesa \
    PORT=7860 \
    LEWELDER_PARTIDAS=por_pestana \
    LEWELDER_MAX_PARTIDAS=6

# La tabla de alcance del robot (unos segundos) se calcula al construir y queda en salidas/alcance.
RUN python -c "from lewelder.alcance import Alcance; Alcance().preparar()"

EXPOSE 7860
CMD ["python", "-m", "lewelder.simulador", "--host", "0.0.0.0"]
