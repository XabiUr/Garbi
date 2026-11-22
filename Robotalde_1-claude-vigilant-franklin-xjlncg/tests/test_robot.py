"""Interfaz del robot y sustituto cinemático."""
import asyncio

import numpy as np
import pytest

from lewelder.contrato import ALTURA_PUNTA, LONGITUD_CORDON, Muestra, instruccion_soldar
from lewelder.robot import POLITICAS, Robot, RobotCinematico, validar_politica

INSTRUCCION = instruccion_soldar("recta", "B")


def test_cumple_la_interfaz():
    r = RobotCinematico()
    assert isinstance(r, Robot)
    e = r.estado()
    assert e["politica"] == "vla" and e["ocupado"] is False and e["punta"] is None


def test_politicas():
    assert POLITICAS == ("vla", "act", "replay")
    assert validar_politica("ACT") == "act"
    with pytest.raises(ValueError):
        validar_politica("pi0")
    with pytest.raises(ValueError):
        RobotCinematico(politica="otra")


@pytest.mark.asyncio
async def test_recorre_el_cordon_completo_aunque_haya_huecos():
    r = RobotCinematico(escala_tiempo=200)
    vistas: list[Muestra] = []
    recorrido = await r.soldar("recta", "B", INSTRUCCION, [(40.0, 55.0)], vistas.append)
    assert vistas == recorrido
    x = np.array([m.x for m in recorrido])
    z = np.array([m.z for m in recorrido])
    assert x.min() < 0 and x.max() > LONGITUD_CORDON  # empieza antes y acaba después del cordón
    sobre = (z < ALTURA_PUNTA + 2) & (x >= 0) & (x <= LONGITUD_CORDON)
    assert np.all(np.diff(x[sobre]) > -1.0)  # avanza (con algo de ruido)
    assert np.abs([m.y for m in recorrido]).max() < 4.0
    t = np.array([m.t for m in recorrido])
    v = np.diff(x[sobre]) / np.diff(t[sobre])
    assert np.median(v) == pytest.approx(5.0, abs=0.5)  # velocidad de soldadura realista
    assert not any(m.gatillo for m in recorrido)  # el LED lo decide el servidor
    assert r.ocupado is False and r.estado()["progreso"] == pytest.approx(1.0)
    assert r.estado()["instruccion"] == INSTRUCCION


@pytest.mark.asyncio
async def test_acepta_callback_asincrono_y_cambio_de_politica_en_caliente():
    r = RobotCinematico(escala_tiempo=200)
    politicas = []

    async def al_moverse(m):
        politicas.append(r.politica)
        if len(politicas) == 50:
            r.cambiar_politica("act")
        await asyncio.sleep(0)

    await r.soldar("t", "D", instruccion_soldar("t", "D"), None, al_moverse)
    assert politicas[0] == "vla" and politicas[-1] == "act"
    assert r.cambios_politica and r.cambios_politica[0][1] == "act"


@pytest.mark.asyncio
async def test_parar_y_no_soldar_dos_veces():
    r = RobotCinematico(escala_tiempo=5)
    tarea = asyncio.create_task(r.soldar("recta", "A", INSTRUCCION, None, lambda m: None))
    await asyncio.sleep(0.05)
    assert r.ocupado
    with pytest.raises(RuntimeError):
        await r.soldar("recta", "A", INSTRUCCION, None, lambda m: None)
    r.parar()
    recorrido = await asyncio.wait_for(tarea, 1.0)
    assert recorrido[-1].x < LONGITUD_CORDON and not r.ocupado


@pytest.mark.asyncio
async def test_tiempo_real_con_escala():
    r = RobotCinematico(escala_tiempo=40)
    inicio = asyncio.get_running_loop().time()
    recorrido = await r.soldar("recta", "B", INSTRUCCION, None, lambda m: None)
    duracion = asyncio.get_running_loop().time() - inicio
    assert duracion == pytest.approx(recorrido[-1].t / 40, rel=0.3, abs=0.1)
