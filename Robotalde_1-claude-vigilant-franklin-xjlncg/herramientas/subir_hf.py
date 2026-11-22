"""Sube a Hugging Face el dataset simulado de LeWelder y los modelos entrenados.

Los datasets y modelos no van al repositorio de GitHub (ver CLAUDE.md): van a Hugging Face, y desde allí se
descargan en el portátil con GPU (ACT) o en la nube (SmolVLA) para entrenar o desplegar.

Token: en la nube de Claude el proxy añade la cabecera `Authorization` a las peticiones a huggingface.co, así que
basta con un valor de relleno en `HF_TOKEN` (este script lo pone si no hay ninguno). En un PC normal: `hf auth login`.

Uso:
    python herramientas/subir_hf.py quien      # comprueba el token y muestra el usuario
    python herramientas/subir_hf.py dataset datos/lewelder_sim_160 --nombre lewelder_sim_160
    python herramientas/subir_hf.py modelo salidas/entreno_act/checkpoints/last/pretrained_model --nombre lewelder_act
Los repositorios se crean privados salvo que se pase --publico.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("HF_TOKEN", "hf_relleno_el_proxy_pone_el_real")
os.environ.pop("HF_HUB_OFFLINE", None)

from huggingface_hub import HfApi  # noqa: E402


def usuario(api: HfApi) -> str:
    return api.whoami()["name"]


def subir_dataset(ruta: Path, repo_id: str, privado: bool) -> str:
    """Sube un LeRobotDataset local con `push_to_hub`, que además etiqueta la versión del formato (la necesita
    `LeRobotDataset` al descargarlo)."""
    from lerobot.datasets import LeRobotDataset

    ds = LeRobotDataset(repo_id=f"local/{ruta.name}", root=ruta)
    ds.repo_id = repo_id
    ds.meta.repo_id = repo_id
    ds.push_to_hub(private=privado, tags=["lewelder", "so101", "simulacion", "soldadura"],
                   upload_large_folder=True)
    return f"https://huggingface.co/datasets/{repo_id}"


def subir_modelo(ruta: Path, repo_id: str, privado: bool) -> str:
    if not (ruta / "config.json").exists():
        raise SystemExit(f"{ruta} no parece un `pretrained_model` de LeRobot (falta config.json)")
    api = HfApi()
    api.create_repo(repo_id, repo_type="model", private=privado, exist_ok=True)
    api.upload_folder(repo_id=repo_id, folder_path=str(ruta), repo_type="model",
                      commit_message=f"LeWelder: {ruta}")
    return f"https://huggingface.co/{repo_id}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("que", choices=["dataset", "modelo", "quien"])
    p.add_argument("ruta", nargs="?", type=Path)
    p.add_argument("--nombre", help="nombre del repositorio en HF (sin usuario)")
    p.add_argument("--usuario", help="usuario u organización de HF (por defecto, el del token)")
    p.add_argument("--publico", action="store_true")
    a = p.parse_args()

    api = HfApi()
    yo = a.usuario or usuario(api)
    if a.que == "quien":
        print(f"Token válido: usuario {yo}")
        return
    if a.ruta is None or not a.ruta.exists():
        raise SystemExit("Falta la ruta o no existe")
    repo_id = f"{yo}/{a.nombre or a.ruta.name}"
    subir = subir_dataset if a.que == "dataset" else subir_modelo
    print("Subido:", subir(a.ruta, repo_id, privado=not a.publico))


if __name__ == "__main__":
    main()
