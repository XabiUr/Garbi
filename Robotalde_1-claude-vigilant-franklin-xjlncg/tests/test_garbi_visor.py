"""El visor 3D (garbi.ver) sin ventana: recorre las situaciones y un ciclo con un visor de mentira."""
import contextlib

import pytest

from garbi import ver


class VisorDeMentira:
    def __init__(self):
        self.textos = []

    @contextlib.contextmanager
    def lock(self):
        yield

    def set_texts(self, textos):
        self.textos.append(textos[0][2])

    def sync(self):
        pass

    def is_running(self):
        return True


def test_visor_recorre_las_situaciones():
    v = ver.Visor()
    falso = VisorDeMentira()
    for _ in range(ver.TOTAL):
        v.situacion(falso)
        v.tecla(ver.TECLA_DERECHA)
    assert len(falso.textos) == ver.TOTAL
    assert falso.textos[0].startswith("S1/") and falso.textos[-1].startswith(f"S{ver.TOTAL}/")


def test_visor_guion_en_directo(monkeypatch):
    monkeypatch.setattr(ver.time, "sleep", lambda s: None)
    v = ver.Visor()
    v.pedido = None
    falso = VisorDeMentira()
    v.guion(falso)
    assert falso.textos[-1] == "Guion terminado"
    for n in range(1, 6):  # los 5 intentos, cada uno con su ciclo completo
        for paso in ("1. Entra el taladro", "3. Preapunto", "4. Se acerca", "5. Taladras", "8. Va a limpiar",
                     "ACT · limpia la zona", "9. Revisa"):
            assert any(t.startswith(f"Intento {n}/5 · {paso}") for t in falso.textos), (n, paso)
    assert any(t.startswith("Cierre: pasada por toda la madera (no puntúa)") for t in falso.textos)
    assert any(t.startswith("Fin: todo limpio") for t in falso.textos)
    assert not any("Te deja sitio" in t or "limpia aqui" in t for t in falso.textos)
    assert v._maqueta.sin_postura.count("acompañar") == 0 and v._maqueta.sin_postura.count("partida") == 0
