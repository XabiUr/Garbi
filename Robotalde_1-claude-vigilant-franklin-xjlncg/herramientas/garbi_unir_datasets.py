"""Une varios LeRobotDataset locales del paso 7 en uno (p. ej. espiral + persecución, o la 1.ª vuelta + la 2.ª).

    python herramientas/garbi_unir_datasets.py --salida datos/garbi_v1 --repo-id local/garbi_v1 \\
        datos/v1_espiral datos/v1_persecucion

Usa `lerobot.datasets.aggregate.aggregate_datasets` (LeRobot 0.7) y junta también los `episodios_garbi_limpiar.json`
de cada uno en el de salida (con el origen de cada episodio).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def unir(origenes: list[Path], salida: Path, repo_id: str) -> dict:
    from lerobot.datasets.aggregate import aggregate_datasets
    from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata

    origenes = [Path(o) for o in origenes]
    repo_ids = [LeRobotDatasetMetadata("local/x", root=o).repo_id for o in origenes]
    aggregate_datasets(repo_ids, repo_id, roots=origenes, aggr_root=Path(salida))
    registro = {"repo_id": repo_id, "origenes": [], "guardados": 0, "descartados": 0}
    for o in origenes:
        f = o / "episodios_garbi_limpiar.json"
        if f.exists():
            r = json.loads(f.read_text())
            registro["origenes"].append({"ruta": str(o), **{k: v for k, v in r.items() if k != "episodios"}})
            registro["guardados"] += r.get("guardados", 0)
            registro["descartados"] += r.get("descartados", 0)
    (Path(salida) / "episodios_garbi_limpiar.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False))
    return registro


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("origenes", nargs="+", type=Path)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--repo-id", default="local/garbi_limpiar")
    a = p.parse_args(argv)
    r = unir(a.origenes, a.salida, a.repo_id)
    print(f"{r['guardados']} episodios en {a.salida} ({r['descartados']} descartados al grabar)")


if __name__ == "__main__":
    main()
