"""Tests del reconocimiento de juntas (v2): geometría pura y de punta a punta con la escena estéreo sintética."""
import numpy as np
import pytest

from lewelder import contrato as c
from lewelder.juntas import (
    CENTRO_MOVIL,
    EstadoJunta,
    Pose,
    apoyada,
    esquinas_marcador,
    marco_cordon,
    pose_base,
    pose_movil_montada,
    pose_movil_tumbada,
    posicion_soldeo,
    punta_en_cordon,
    reconocer_junta,
    rot_x,
    rot_y,
)


# --- geometría ---------------------------------------------------------------------------------------------------
def test_pose_base_por_defecto_sigue_el_contrato():
    base = pose_base()
    assert np.allclose(base.t, [c.POSICION_BASE.x, c.POSICION_BASE.y, c.GROSOR_CHAPA])
    # Giro 0: la X de la base apunta a +Y de la mesa.
    assert np.allclose(base.R[:, 0], [0, 1, 0], atol=1e-12)
    assert np.allclose(base.R[:, 2], [0, 0, 1], atol=1e-12)


def test_movil_en_t_ocupa_la_linea_central_de_la_base():
    base = pose_base()
    en_base = base.inversa() @ pose_movil_montada(c.TipoJunta.T, base)
    # Marco del contrato de hardware: montada, los ejes de la móvil son los de la base; cara lisa en Y = 0, el canto
    # que apoya 2 mm dentro de la ranura.
    assert np.allclose(en_base.R, np.eye(3), atol=1e-12)
    assert np.allclose(en_base.aplicar([0.0, -c.GROSOR_CHAPA / 2, 0.0]), [0.0, 0.0, c.Z_CANTO_MOVIL[c.TipoJunta.T]])


def test_movil_en_esquina_junto_al_tope():
    base = pose_base()
    en_base = base.inversa() @ pose_movil_montada(c.TipoJunta.ESQUINA, base)
    caja = en_base.aplicar([[x, y, z] for x in (-70, 70) for y in (-3, 3) for z in (0, 40)])
    assert np.allclose(caja[:, 1].min(), 31.0) and np.allclose(caja[:, 1].max(), 37.0)  # el tope ocupa 37..40
    assert np.allclose(caja[:, 2].min(), 0.0)


def test_esquinas_de_los_marcadores_como_en_el_contrato_de_hardware():
    base_m = esquinas_marcador(c.ID_BASE)
    assert np.allclose(base_m.mean(axis=0), c.ARUCO_EN_BASE)
    lisa = esquinas_marcador(c.IDS_MOVIL["cara_lisa"])
    aleta = esquinas_marcador(c.IDS_MOVIL["cara_aleta"])
    assert np.allclose(lisa[:, 1], -c.GROSOR_CHAPA / 2) and np.allclose(aleta[:, 1], c.GROSOR_CHAPA / 2)
    assert np.allclose(lisa.mean(axis=0)[[0, 2]], c.ARUCO_EN_MOVIL)
    # Tabla de hardware/v2/contrato.md: +X del 41 = +X de la chapa, +X del 40 = -X de la chapa, arriba = +Z.
    assert np.allclose(lisa[1] - lisa[0], [c.LADO_ARUCO_V2, 0, 0]) and np.allclose(aleta[1] - aleta[0], [-25, 0, 0])
    assert np.allclose(lisa[0] - lisa[3], [0, 0, c.LADO_ARUCO_V2]) and np.allclose(aleta[0] - aleta[3], [0, 0, 25])
    # Orden de OpenCV visto desde fuera de la cara: X del marcador (esq1 - esq0) x Y (esq0 - esq3) = normal hacia fuera.
    for esq, normal_fuera in ((lisa, [0, -1, 0]), (aleta, [0, 1, 0]), (base_m, [0, 0, 1])):
        n = np.cross(esq[1] - esq[0], esq[0] - esq[3])
        assert np.dot(n, normal_fuera) > 0


@pytest.mark.parametrize("tipo", list(c.TipoJunta))
def test_marco_cordon_igual_que_alcance(tipo):
    from lewelder import alcance

    for anclaje in (c.POSICION_BASE, c.Anclaje("x", 230.0, -40.0, 35.0)):
        origen, R = alcance.marco_cordon(tipo, anclaje)
        for base in (anclaje, pose_base(anclaje=anclaje)):
            cordon = marco_cordon(tipo, base)
            assert np.allclose(cordon.t, origen) and np.allclose(cordon.R, R)


def test_marco_cordon_t():
    base = pose_base()
    cordon = marco_cordon(c.TipoJunta.T, base)
    # Inicio del cordón en X = -60 de la base, sobre la cara superior; X del cordón = X de la base.
    assert np.allclose(cordon.t, base.aplicar([-c.LONGITUD_CORDON / 2, 0.0, 0.0]))
    assert np.allclose(cordon.R, base.R)
    # El alma (chapa móvil) queda en Y >= 0 del marco del cordón, como en la v1.
    movil = pose_movil_montada(c.TipoJunta.T, base)
    assert cordon.inversa().aplicar(movil.aplicar(CENTRO_MOVIL))[1] > 0


# --- reconocimiento con poses exactas -----------------------------------------------------------------------------
@pytest.mark.parametrize("tipo", list(c.TipoJunta))
@pytest.mark.parametrize("giro", [0.0, 30.0, -45.0, 90.0, 180.0])
def test_reconoce_juntas_montadas(tipo, giro):
    base = pose_base(250.0, 10.0, giro)
    junta = reconocer_junta(base, pose_movil_montada(tipo, base))
    assert junta.tipo == EstadoJunta(tipo.value)
    assert junta.completa and junta.tipo_junta is tipo
    assert junta.motivo is None and junta.confianza > 0.9
    assert junta.posicion == "PB"
    assert np.allclose(junta.cordon.t, marco_cordon(tipo, base).t)


@pytest.mark.parametrize("inclinacion", [12.0, -8.0])
def test_inclinada_es_incompleta(inclinacion):
    base = pose_base()
    junta = reconocer_junta(base, pose_movil_montada(c.TipoJunta.T, base, inclinacion=inclinacion))
    assert junta.tipo is EstadoJunta.INCOMPLETA and junta.candidata is c.TipoJunta.T
    assert "inclinada" in junta.motivo and f"{abs(inclinacion):.0f}°" in junta.motivo


def test_desplazada_de_la_guia_es_incompleta():
    base = pose_base()
    junta = reconocer_junta(base, pose_movil_montada(c.TipoJunta.ESQUINA, base, desplazamiento=(0.0, -8.0, 0.0)))
    assert junta.tipo is EstadoJunta.INCOMPLETA and junta.candidata is c.TipoJunta.ESQUINA
    assert "8 mm de la guía" in junta.motivo


def test_levantada_y_corrida_son_incompletas():
    base = pose_base()
    alta = reconocer_junta(base, pose_movil_montada(c.TipoJunta.T, base, desplazamiento=(0.0, 0.0, 7.0)))
    assert alta.tipo is EstadoJunta.INCOMPLETA and "apoya" in alta.motivo
    corrida = reconocer_junta(base, pose_movil_montada(c.TipoJunta.T, base, desplazamiento=(25.0, 0.0, 0.0)))
    assert corrida.tipo is EstadoJunta.INCOMPLETA and "a lo largo" in corrida.motivo
    girada = reconocer_junta(base, pose_movil_montada(c.TipoJunta.T, base, giro=10.0))
    assert girada.tipo is EstadoJunta.INCOMPLETA and "girada" in girada.motivo


def test_pequenos_errores_se_toleran():
    base = pose_base()
    junta = reconocer_junta(base, pose_movil_montada(c.TipoJunta.T, base, inclinacion=2.0,
                                                     desplazamiento=(3.0, 1.0, 0.5)))
    assert junta.tipo is EstadoJunta.T and 0.5 < junta.confianza < 1.0


def test_tumbada_y_sin_movil():
    base = pose_base()
    tumbada = reconocer_junta(base, pose_movil_tumbada(135.0, 195.0, 20.0))
    assert tumbada.tipo is EstadoJunta.INCOMPLETA and "tumbada" in tumbada.motivo
    assert tumbada.cordon is None or tumbada.candidata is None
    sin = reconocer_junta(base, None)
    assert sin.tipo is EstadoJunta.SIN_MOVIL and sin.cordon is None and sin.posicion is None
    nada = reconocer_junta(None, pose_movil_tumbada(135.0, 195.0, 0.0))
    assert nada.tipo is EstadoJunta.SIN_BASE


def test_posicion_de_soldeo_segun_la_gravedad():
    base = pose_base()
    assert posicion_soldeo(c.TipoJunta.T, base) == "PB"
    # Cordón vertical (base de pie, X de la base hacia arriba): vertical ascendente.
    de_pie = Pose(base.R @ rot_y(-90.0), base.t)
    assert posicion_soldeo(c.TipoJunta.T, de_pie) == "PF"
    assert posicion_soldeo(c.TipoJunta.T, Pose(base.R @ rot_y(90.0), base.t)) == "PG"
    # Junta girada 45° alrededor del cordón: la bisectriz del ángulo mira arriba → plana (PA).
    assert posicion_soldeo(c.TipoJunta.T, Pose(base.R @ rot_x(-45.0), base.t)) == "PA"
    # Boca abajo: bajo techo en ángulo (PD).
    assert posicion_soldeo(c.TipoJunta.T, Pose(base.R @ rot_x(180.0), base.t)) == "PD"


def test_punta_en_cordon_y_apoyo():
    base = pose_base(240.0, -20.0, 25.0)
    junta = reconocer_junta(base, pose_movil_montada(c.TipoJunta.ESQUINA, base))
    p_cordon = np.array([40.0, -2.0, 1.2])
    p_mesa = junta.cordon.aplicar(p_cordon)
    assert np.allclose(punta_en_cordon(p_mesa, junta), p_cordon)
    assert apoyada(0.0) and apoyada(1.5) and apoyada(-0.8)
    assert not apoyada(c.ALTURA_APOYO + 0.1) and not apoyada(5.0) and not apoyada(-15.0)
    with pytest.raises(ValueError):
        punta_en_cordon(p_mesa, reconocer_junta(base, None))


def test_con_una_sola_camara_se_amplian_las_tolerancias_de_posicion():
    from lewelder.juntas import TOLERANCIAS_UNA_CAMARA

    base = pose_base()
    movil = pose_movil_montada(c.TipoJunta.T, base, desplazamiento=(0.0, -4.0, 0.0))
    assert reconocer_junta(base, movil).tipo is EstadoJunta.INCOMPLETA
    assert reconocer_junta(base, movil, tolerancias=TOLERANCIAS_UNA_CAMARA).tipo is EstadoJunta.T
    # Los ángulos no se relajan: la orientación se mide bien también con una cámara.
    volcada = pose_movil_montada(c.TipoJunta.T, base, inclinacion=8.0)
    assert reconocer_junta(base, volcada, tolerancias=TOLERANCIAS_UNA_CAMARA).tipo is EstadoJunta.INCOMPLETA
