#!/usr/bin/env bash
# Entrena el ACT de Garbi con LeRobot 0.7. Por defecto el del ACERCAMIENTO (solución final, 20-11: de la posición
# prudente a la de aspirar junto a la broca clavada); con QUE=limpiar, el del paso 7 del ciclo viejo (M5).
#
# Uso:
#   herramientas/garbi_entrenar.sh hf      # en Hugging Face Jobs (A10G pequeña), ~30k pasos, lote 8 (de pago)
#   herramientas/garbi_entrenar.sh local   # en este equipo (GPU CUDA; en Mac pon DISPOSITIVO=mps)
#   herramientas/garbi_entrenar.sh cpu     # en CPU a resolución reducida (la receta de la prueba en simulación)
#   herramientas/garbi_entrenar.sh humo    # 2 pasos en CPU con un modelo diminuto: comprueba que todo encaja
#   herramientas/garbi_entrenar.sh evaluar # cada checkpoint (10k, 20k, 30k) en la sesión simulada del ciclo final
#
# Datasets del acercamiento: herramientas/garbi_grabar_acercamiento.py --sim (simulación, acercamiento programado con
# recuperaciones) y herramientas/garbi_teleop_grabar.py --corte auto (robot real teleoperado). Episodios de la clavada
# a la levantada; «observation.state» = la orden anterior (el mismo convenio que el ciclo final al ejecutar).
#
# Variables (con valores por defecto):
#   QUE          acercamiento (por defecto) o limpiar
#   HF_USUARIO   usuario u organización del Hub
#   DATASET      repo del dataset (grabado con herramientas/garbi_grabar.py --push y los teleoperados)
#   DATASET_RAIZ carpeta local del dataset (solo local/humo; si no, lo baja del Hub)
#   POLITICA     repo del modelo en el Hub
#   PASOS, LOTE, DISPOSITIVO, SALIDA
#
# Flags comprobados con `lerobot-train --policy.type=act --help` (LeRobot 0.7.0):
#   --job.target (sabor de HF Jobs; vacío o "local" = este equipo), --job.timeout, --job.detach,
#   --dataset.image_transforms.enable (aumentos de imagen: brillo, contraste, saturación, tono, nitidez, afín),
#   --policy.push_to_hub, --policy.repo_id, --policy.private, --save_checkpoint_to_hub, --save_freq.
# Seguir el trabajo remoto: hf jobs ps · hf jobs logs <id> · cancelar: hf jobs cancel <id>
set -euo pipefail

MODO="${1:-hf}"
HF_USUARIO="${HF_USUARIO:-Izaguirre97}"
QUE="${QUE:-acercamiento}"
if [ "$QUE" = "limpiar" ]; then
  DATASET="${DATASET:-$HF_USUARIO/garbi_limpiar}"
  POLITICA="${POLITICA:-$HF_USUARIO/garbi_act}"
  SALIDA="${SALIDA:-salidas/garbi_act}"
else
  DATASET="${DATASET:-$HF_USUARIO/garbi_acercamiento}"
  POLITICA="${POLITICA:-$HF_USUARIO/garbi_act_acercamiento}"
  SALIDA="${SALIDA:-salidas/garbi_act_acercamiento}"
fi
PASOS="${PASOS:-30000}"
LOTE="${LOTE:-8}"
# Checkpoints cada 10k (10k, 20k, 30k): se evalúan los tres en la simulación (modo evaluar) y en el robot
GUARDAR_CADA="${GUARDAR_CADA:-10000}"
LEROBOT_TRAIN="${LEROBOT_TRAIN:-lerobot-train}"

COMUNES=(
  --policy.type=act
  --dataset.repo_id="$DATASET"
  --dataset.image_transforms.enable=true
  --batch_size="$LOTE"
  --steps="$PASOS"
  --job_name="$(basename "$POLITICA")"
)

case "$MODO" in
  hf)
    # Lo lanza el propio lerobot-train: sube la configuración a HF Jobs y entrena allí con la imagen de LeRobot.
    # El dataset tiene que estar en el Hub. Cada checkpoint se sube al repo del modelo (no se pierde si se corta).
    exec "$LEROBOT_TRAIN" "${COMUNES[@]}" \
      --job.target=a10g-small --job.timeout="${LIMITE:-6h}" --job.detach=true \
      --policy.device=cuda --policy.repo_id="$POLITICA" --policy.push_to_hub=true --policy.private=true \
      --save_checkpoint_to_hub=true --save_freq="$GUARDAR_CADA" --log_freq=100 \
      --output_dir=/tmp/salida
    ;;
  local)
    RAIZ=()
    [ -n "${DATASET_RAIZ:-}" ] && RAIZ=(--dataset.root="$DATASET_RAIZ")
    exec "$LEROBOT_TRAIN" "${COMUNES[@]}" "${RAIZ[@]}" \
      --policy.device="${DISPOSITIVO:-cuda}" --policy.push_to_hub=false \
      --save_freq="$GUARDAR_CADA" --log_freq=100 --output_dir="$SALIDA"
    ;;
  cpu)
    # La receta con la que se validó la tubería en la simulación (.plans/aspira/act-simulacion.md): dataset a
    # 160×120, ACT más pequeño (dim_model 256), chunk de 50 y lr 1e-4. OJO: limitar los hilos (OMP_NUM_THREADS) a
    # los núcleos libres; con más hilos que núcleos (otro proceso o el dataloader) cada paso iba 50 veces más lento.
    : "${DATASET_RAIZ:?cpu necesita DATASET_RAIZ (carpeta del dataset local)}"
    export OMP_NUM_THREADS="${HILOS:-2}" MKL_NUM_THREADS="${HILOS:-2}"
    exec "$LEROBOT_TRAIN" --policy.type=act --dataset.repo_id="$DATASET" --dataset.root="$DATASET_RAIZ" \
      --dataset.image_transforms.enable=true --policy.device=cpu --policy.push_to_hub=false \
      --policy.chunk_size=50 --policy.n_action_steps=25 --policy.dim_model=256 --policy.dim_feedforward=1024 \
      --policy.optimizer_lr=1e-4 --policy.optimizer_lr_backbone=1e-5 \
      --batch_size="${LOTE_CPU:-8}" --steps="${PASOS_CPU:-8000}" --num_workers=1 --log_freq=100 --save_freq=2000 \
      --output_dir="$SALIDA" --job_name="$(basename "$POLITICA")" ${REANUDAR:+--resume=true --config_path="$REANUDAR"}
    ;;
  humo)
    # Solo para comprobar el encaje dataset → entrenamiento → HabilidadACT (tests/test_garbi_habilidad.py).
    : "${DATASET_RAIZ:?humo necesita DATASET_RAIZ (carpeta del dataset local)}"
    exec "$LEROBOT_TRAIN" --policy.type=act --dataset.repo_id="$DATASET" --dataset.root="$DATASET_RAIZ" \
      --dataset.image_transforms.enable=true \
      --policy.device=cpu --policy.push_to_hub=false --policy.pretrained_backbone_weights=null \
      --policy.chunk_size=10 --policy.n_action_steps=10 --policy.dim_model=64 --policy.dim_feedforward=128 \
      --steps="${PASOS_HUMO:-2}" --batch_size=2 --num_workers=0 --save_freq="${PASOS_HUMO:-2}" --log_freq=1 \
      --output_dir="$SALIDA" --job_name=garbi_act_humo
    ;;
  evaluar)
    # Cada checkpoint de $SALIDA/checkpoints (o los de CHECKPOINTS="ruta1 ruta2 ...", p. ej. bajados del Hub con
    # `hf download $POLITICA --local-dir ...`) en la sesión simulada del ciclo final (5 intentos y variantes) con ACT
    # en el ACERCAMIENTO. Mira «aciertos», «holgura mín», «borde mín», «respaldos» y «frenadas de la habilidad».
    PY="${PY:-python}"
    export OMP_NUM_THREADS="${HILOS:-2}"
    for ck in ${CHECKPOINTS:-$(ls -d "$SALIDA"/checkpoints/*/pretrained_model 2>/dev/null)}; do
      echo "=== $ck"
      "$PY" -m garbi.correr --sim --verdad --acercamiento act --modelo "$ck" 2>&1 | grep "juez:"
    done
    ;;
  *) echo "Modo desconocido: $MODO (hf, local, cpu, humo o evaluar)"; exit 1 ;;
esac
