#!/usr/bin/env bash
# Entrena las políticas de LeWelder en una GPU de Hugging Face Jobs (sin PC propio).
#
# El trabajo descarga el dataset del Hub, entrena con LeRobot 0.7 y sube al Hub cada punto de control y el
# modelo final (si se corta, no se pierde lo entrenado hasta el último punto de control).
# Necesita crédito prepagado en la cuenta de Hugging Face y un token con permiso de escritura en HF_TOKEN.
#
# Uso:
#   herramientas/entrenar_hf_jobs.sh act --prueba   # 200 pasos para comprobar que todo funciona (céntimos)
#   herramientas/entrenar_hf_jobs.sh act            # ACT en una L4  (~0,80 $/h; estimado 1-2 h)
#   herramientas/entrenar_hf_jobs.sh smolvla        # SmolVLA en una A10G (~1 $/h; estimado 3-4 h)
# Seguir el trabajo: hf jobs ps · hf jobs logs <id> · cancelar: hf jobs cancel <id>
set -euo pipefail

USUARIO="${HF_USUARIO:-Izaguirre97}"
DATASET="${HF_DATASET:-$USUARIO/lewelder_sim_160}"
POLITICA="${1:?Indica act o smolvla}"
PRUEBA="${2:-}"

case "$POLITICA" in
  act)
    FLAVOR="${FLAVOR:-l4x1}"; PASOS=40000; GUARDAR=5000; LIMITE=4h
    REPO="$USUARIO/act_lewelder"
    ARGS="--policy.type=act --batch_size=16 --num_workers=6"
    EXTRAS="dataset,training"
    ;;
  smolvla)
    FLAVOR="${FLAVOR:-a10g-small}"; PASOS=20000; GUARDAR=2500; LIMITE=6h
    REPO="$USUARIO/smolvla_lewelder"
    # Nombres de cámara que espera SmolVLA (RENOMBRE_SMOLVLA del contrato) y una tercera cámara vacía.
    ARGS="--policy.path=lerobot/smolvla_base --batch_size=32 --num_workers=3 --policy.empty_cameras=1"
    ARGS="$ARGS --rename_map='{\"observation.images.cenital\":\"observation.images.camera1\",\"observation.images.muneca\":\"observation.images.camera2\"}'"
    EXTRAS="dataset,training,smolvla"
    ;;
  *) echo "Política desconocida: $POLITICA (act o smolvla)"; exit 1 ;;
esac

if [ "$PRUEBA" = "--prueba" ]; then
  PASOS=200; GUARDAR=200; LIMITE=40m; REPO="${REPO}_prueba"
fi

# Dentro del trabajo: instalar LeRobot, entrenar y subir (`--policy.repo_id` + push_to_hub sube el modelo final).
ORDEN="pip install -q 'lerobot[$EXTRAS]==0.7.0' && \
lerobot-train --dataset.repo_id=$DATASET $ARGS --policy.device=cuda \
  --policy.repo_id=$REPO --policy.push_to_hub=true --policy.private=true --save_checkpoint_to_hub=true \
  --steps=$PASOS --save_freq=$GUARDAR --log_freq=100 \
  --output_dir=/tmp/salida --job_name=$(basename "$REPO")"

echo "Lanzando $POLITICA en $FLAVOR ($PASOS pasos, límite $LIMITE) → https://huggingface.co/$REPO"
hf jobs run --detach --flavor "$FLAVOR" --timeout "$LIMITE" --secrets HF_TOKEN \
  python:3.12 bash -c "$ORDEN"  # LeRobot 0.7 exige Python >= 3.12; PyTorch con CUDA llega desde PyPI
