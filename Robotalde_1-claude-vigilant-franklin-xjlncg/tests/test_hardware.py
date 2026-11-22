"""Tests del generador de hardware (`herramientas/generar_hardware.py`)."""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("generar_hardware", RAIZ / "herramientas" / "generar_hardware.py")
gh = importlib.util.module_from_spec(_spec)
sys.modules["generar_hardware"] = gh  # las dataclass lo necesitan registrado
_spec.loader.exec_module(gh)
c = gh.c  # el mismo contrato que usa el generador


@pytest.fixture(scope="module")
def generado(tmp_path_factory):
    salida = tmp_path_factory.mktemp("hardware")
    res = gh.generar(salida, verificar=True)
    return salida, res


# --- el script corre y genera todo -------------------------------------------------------------------------------
def test_script_corre_en_directorio_temporal(tmp_path):
    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "generar_hardware.py"), "--salida", str(tmp_path),
                        "--sin-verificar"], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    for rel in ("contrato.md", "lista_material.md", "aruco/marcadores_a4.pdf", "aruco/tablero_calibracion_a4.pdf",
                "planos/pieza_recta_superior.png", "planos/pieza_t_seccion.svg", "planos/loseta_anclaje.png",
                "planos/base_anclajes.png", "planos/camara_seguimiento.png"):
        assert (tmp_path / rel).is_file(), rel


def test_genera_archivos_y_aviso_de_solapes(generado):
    salida, res = generado
    md = (salida / "contrato.md").read_text(encoding="utf-8")
    assert "## Avisos" in md
    if res["problemas"]:
        # el documento debe avisar de forma visible
        assert "Los anclajes del contrato se solapan" in md
    else:
        assert "Sin solapes" in md
        assert "se solapan" not in md
    assert "Propuesta de anclajes" not in md
    assert not (salida / "planos" / "base_anclajes_propuesta.png").exists()
    for n in c.ANCLAJES:
        assert f"| {n} |" in md  # cada anclaje en la tabla de posiciones
    assert "☐" in (salida / "lista_material.md").read_text(encoding="utf-8")


def test_idempotente(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    gh.generar(a, verificar=False)
    gh.generar(b, verificar=False)
    for rel in ("contrato.md", "lista_material.md", "aruco/marcadores_a4.pdf", "aruco/aruco_10_recta.png",
                "planos/base_anclajes.svg", "planos/loseta_anclaje.png"):
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


# --- convenciones y solapes --------------------------------------------------------------------------------------
def test_convencion_de_giro():
    an = c.Anclaje("X", 100.0, 50.0, 0.0)
    assert np.allclose(gh.a_mesa(an, 10.0, 0.0), (100.0, 60.0))  # X de la pieza → +Y de la mesa
    assert np.allclose(gh.a_mesa(an, 0.0, 10.0), (90.0, 50.0))  # Y de la pieza → −X de la mesa
    an90 = c.Anclaje("X", 0.0, 0.0, -90.0)
    assert np.allclose(gh.a_mesa(an90, 10.0, 0.0), (10.0, 0.0))  # giro −90: el cordón avanza en +X
    assert np.allclose(gh.a_pieza(an, *gh.a_mesa(an, 12.0, -7.0)), (12.0, -7.0))


def test_detecta_solape_sintetico():
    iguales = {"A": c.Anclaje("A", 200.0, 0.0, 0.0), "B": c.Anclaje("B", 210.0, 5.0, 0.0)}
    tipos = {p.tipo for p in gh.comprobar_huellas(iguales)}
    assert {"pieza", "loseta"} <= tipos
    assert not gh.huellas_sin_solape(iguales)


def test_no_detecta_solape_si_estan_lejos():
    lejos = {"A": c.Anclaje("A", 200.0, -400.0, 0.0), "B": c.Anclaje("B", 200.0, 400.0, 90.0)}
    assert gh.comprobar_huellas(lejos) == []
    assert gh.huellas_sin_solape(lejos)


def test_losetas_demasiado_juntas_y_robot():
    lx0, _, lx1, _ = gh.loseta_local()
    largo = lx1 - lx0
    # dos losetas giro 0 en fila a lo largo de Y casi pegadas (0,2 mm): no se solapan pero están demasiado juntas
    juntas = {"A": c.Anclaje("A", 250.0, 0.0, 0.0), "B": c.Anclaje("B", 250.0, largo + 0.2, 0.0)}
    probs = gh.comprobar_huellas(juntas)
    assert [p.tipo for p in probs] == ["loseta"]
    assert probs[0].area == 0 and 0.1 < probs[0].separacion < 0.3
    encima = {"A": c.Anclaje("A", 40.0, -60.0, 0.0)}
    assert [p.tipo for p in gh.comprobar_huellas(encima)] == ["robot"]


def test_interseccion_de_rectangulos_girados():
    a = [(0, 0), (10, 0), (10, 10), (0, 10)]
    b = [(5, 5), (15, 5), (15, 15), (5, 15)]
    assert gh.area_solape(a, b) == pytest.approx(25.0)
    rombo = [(5, -2), (12, 5), (5, 12), (-2, 5)]
    assert 0 < gh.area_solape(a, rombo) < 100
    assert gh.separacion(a, [(13, 0), (20, 0), (20, 5), (13, 5)]) == pytest.approx(3.0)


# --- webcam de seguimiento ---------------------------------------------------------------------------------------
def test_camara_usa_la_pose_comun_del_software():
    from lewelder.camara_sintetica import PoseCamara

    pose = PoseCamara.por_defecto()
    cam = gh.camara_por_defecto(74.0)
    assert np.allclose(cam.pos, pose.centro)
    # el objetivo de la pose cae en el centro de la imagen
    u, w, z = cam.proyectar(gh.parametros_pose()["objetivo"])
    assert z > 0 and abs(u) < 1e-6 and abs(w) < 1e-6
    assert cam.pos[1] < 0  # azimut negativo: la cámara está del lado −Y (el del anclaje A)


def test_visibilidad_detecta_el_alma():
    # una cámara justo detrás del alma (lado +Y de la pieza, baja) no ve la punta; delante (−Y) sí
    an = c.Anclaje("X", 250.0, 0.0, 0.0)  # Y de la pieza → −X de la mesa
    detras = gh.Camara(np.array([150.0, 60.0, gh.Z_SUPERFICIE + 30.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
                       np.array([0, 0, 1.0]), 90.0, 60.0)
    delante = gh.Camara(np.array([500.0, 60.0, gh.Z_SUPERFICIE + 30.0]), np.array([-1.0, 0, 0]),
                        np.array([0, -1.0, 0]), np.array([0, 0, 1.0]), 90.0, 60.0)
    assert gh.visibilidad_t(an, detras) < 0.5
    assert gh.visibilidad_t(an, delante) == 1.0


def test_camara_por_defecto_ve_la_t_y_los_aruco(generado):
    salida, res = generado
    if res["problemas"]:
        pytest.skip("los anclajes del contrato se solapan: la visibilidad no tiene sentido")
    assert all(f == 1.0 for f in res["visibilidad"].values()), res["visibilidad"]
    assert all(f == 1.0 for f in res["visibilidad_aruco"].values()), res["visibilidad_aruco"]
    assert res["fov_necesario"] <= max(gh.FOV_HORIZONTAL)
    md = (salida / "contrato.md").read_text(encoding="utf-8")
    assert "tapa la punta" not in md.split("## 0.")[0]  # sin aviso de oclusión


def test_la_pieza_y_su_aruco_caben():
    # el recorte del ArUco de la pieza cabe en la chapa, sin pisar la junta ni salirse
    x0, y0, x1, y1 = gh.aruco_pieza_local()
    assert y0 >= -(c.HOLGURA_JUNTA / 2 + c.CHAPA_ANCHO) and y1 <= -c.HOLGURA_JUNTA / 2
    assert x0 >= gh.X_PIEZA[0] and x1 <= gh.X_PIEZA[1]
    # el ArUco del anclaje queda fuera de la huella de la pieza y dentro de la loseta
    ax0, ay0, ax1, ay1 = gh.aruco_anclaje_local()
    lx0, ly0, lx1, ly1 = gh.loseta_local()
    assert ay1 < gh.huella_en_anclaje()[1]
    assert lx0 <= ax0 and ax1 <= lx1 and ly0 <= ay0
    # el margen blanco es de al menos un módulo
    assert gh.MARGEN_BLANCO >= gh.modulo_aruco(c.LADO_ARUCO_PIEZA)


# --- ArUco: ids y escala -----------------------------------------------------------------------------------------
def test_aruco_detectados_con_ids_y_escala(generado):
    salida, res = generado
    ver = res["verificacion"]
    assert ver["hoja_piezas.png"]["ok"] and ver["hoja_anclajes.png"]["ok"]
    assert set(ver["hoja_piezas.png"]["ids"]) == set(c.IDS_PIEZA[c.TipoPieza.RECTA]) | set(c.IDS_PIEZA[c.TipoPieza.T])
    assert set(ver["hoja_anclajes.png"]["ids"]) == set(c.IDS_ANCLAJE)
    for lado in ver["hoja_piezas.png"]["ids"].values():
        assert lado == pytest.approx(c.LADO_ARUCO_PIEZA, abs=0.15)
    assert ver["tablero"]["ok"]


@pytest.mark.parametrize("id_aruco", [10, 29, 0, 3])
def test_png_suelto_a_600_ppp(generado, id_aruco):
    salida, _ = generado
    ruta = salida / "aruco" / gh.nombre_png(id_aruco)
    im = Image.open(ruta)
    assert round(im.info["dpi"][0]) == gh.PPP
    lado = c.LADO_ARUCO_ANCLAJE if id_aruco in c.IDS_ANCLAJE else c.LADO_ARUCO_PIEZA
    # tamaño total = lado + margen blanco, en píxeles a 600 ppp
    assert im.width == round(gh.lado_con_margen(lado) / 25.4 * gh.PPP)
    gris = np.array(im.convert("L"))
    filas = np.where((gris < 128).any(axis=1))[0]
    lado_px = filas[-1] - filas[0] + 1
    assert lado_px == pytest.approx(lado / 25.4 * gh.PPP, abs=1.5)
    det = gh.detectar_aruco(np.pad(gris, 60, constant_values=255), gh.PPP)
    assert list(det) == [id_aruco]


def test_pdf_a4_y_escala(generado):
    salida, res = generado
    datos = (salida / "aruco" / "marcadores_a4.pdf").read_bytes()
    cajas = re.findall(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", datos)
    assert len(cajas) == 2
    for w, h in cajas:
        assert float(w) == pytest.approx(595.276, abs=0.01) and float(h) == pytest.approx(841.89, abs=0.01)
    if res["verificacion"]["marcadores_a4.pdf"] is None:
        pytest.skip("pdftoppm no está instalado: no se puede rasterizar el PDF")
    assert res["verificacion"]["marcadores_a4.pdf"]["ok"]
    for pagina in res["verificacion"]["marcadores_a4.pdf"]["paginas"]:
        for lado in pagina.values():
            assert lado == pytest.approx(25.0, abs=0.15)


# =================================================================================================================
# v2 (`herramientas/generar_hardware_v2.py`)
# =================================================================================================================
_spec2 = importlib.util.spec_from_file_location("generar_hardware_v2",
                                                RAIZ / "herramientas" / "generar_hardware_v2.py")
gh2 = importlib.util.module_from_spec(_spec2)
sys.modules["generar_hardware_v2"] = gh2
_spec2.loader.exec_module(gh2)

ARCHIVOS_V2 = ("contrato.md", "lista_material.md", "aruco/marcadores_v2_a4.pdf", "aruco/hoja_v2.png",
               "aruco/aruco_30_base.png", "aruco/aruco_41_movil_lisa.png", "planos/base_v2_superior.png",
               "planos/base_v2_seccion.svg", "planos/movil_v2.png", "planos/antorcha_soporte_v2.png",
               "planos/camaras_estereo.png", "planos/mesa_v2.svg", "planos/prueba_v2.png")


@pytest.fixture(scope="module")
def generado_v2(tmp_path_factory):
    salida = tmp_path_factory.mktemp("hardware_v2")
    return salida, gh2.generar(salida, verificar=True)


def test_v2_script_corre_con_la_opcion_v2(tmp_path):
    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "generar_hardware.py"), "--v2", "--salida",
                        str(tmp_path), "--sin-verificar"], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    for rel in ARCHIVOS_V2:
        assert (tmp_path / rel).is_file(), rel
    assert not (tmp_path / "planos" / "pieza_t_superior.png").exists()  # la v1 no se mezcla


def test_v2_idempotente(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    gh2.generar(a, verificar=False)
    gh2.generar(b, verificar=False)
    for rel in ARCHIVOS_V2:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def test_v2_documentos(generado_v2):
    salida, res = generado_v2
    md = (salida / "contrato.md").read_text(encoding="utf-8")
    assert "brief_solidworks.md" in md  # enlaza el brief de CAD
    for seccion in ("## Avisos", "## 5. Diseño para que el robot lo consiga", "## 9. Pieza de prueba",
                    "## 11. Lista de comprobación con calibre"):
        assert seccion in md, seccion
    if res["problemas"]:
        assert "Zona libre" in md
    lista = (salida / "lista_material.md").read_text(encoding="utf-8")
    assert "☐" in lista and "2.ª webcam" in lista and "jue" in lista.lower()


# --- ArUco v2: ids y escala --------------------------------------------------------------------------------------
def test_v2_aruco_detectados_con_ids_y_escala(generado_v2):
    _, res = generado_v2
    ver = res["verificacion"]
    esperados = {c.ID_BASE, *c.IDS_MOVIL.values(), 42, 43, 44, 45}
    assert set(gh2.ids_unicos()) == esperados
    assert ver["hoja_v2.png"]["ok"] and set(ver["hoja_v2.png"]["ids"]) == esperados
    for lado in ver["hoja_v2.png"]["ids"].values():
        assert lado == pytest.approx(c.LADO_ARUCO_V2, abs=0.15)
    for i in esperados:
        assert ver[gh2.nombre_png_v2(i)]["ok"], i


def test_v2_pdf_a4_y_escala(generado_v2):
    salida, res = generado_v2
    datos = (salida / "aruco" / "marcadores_v2_a4.pdf").read_bytes()
    cajas = re.findall(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", datos)
    assert len(cajas) == 1
    assert float(cajas[0][0]) == pytest.approx(595.276, abs=0.01)
    assert float(cajas[0][1]) == pytest.approx(841.89, abs=0.01)
    if res["verificacion"]["marcadores_v2_a4.pdf"] is None:
        pytest.skip("pdftoppm no está instalado: no se puede rasterizar el PDF")
    assert res["verificacion"]["marcadores_v2_a4.pdf"]["ok"]


def test_v2_png_suelto_a_600_ppp(generado_v2):
    salida, _ = generado_v2
    im = Image.open(salida / "aruco" / gh2.nombre_png_v2(c.ID_BASE))
    assert round(im.info["dpi"][0]) == gh.PPP
    assert im.width == round(gh.lado_con_margen(c.LADO_ARUCO_V2) / 25.4 * gh.PPP)


# --- las piezas caben --------------------------------------------------------------------------------------------
def test_v2_aleta_dentro_de_la_chapa():
    x0, z0, x1, z1 = gh2.aleta_rect()
    assert -c.LARGO_MOVIL / 2 <= x0 and x1 <= c.LARGO_MOVIL / 2
    assert 0 <= z0 and z1 <= c.ALTO_MOVIL


def test_v2_aruco_de_la_movil_no_pisa_aleta_ni_cordon_ni_imanes():
    chapa = (-c.LARGO_MOVIL / 2, 0.0, c.LARGO_MOVIL / 2, c.ALTO_MOVIL)
    assert gh2.dentro(gh2.aruco_movil(), chapa)
    assert not gh2.solapan(gh2.aruco_movil(), gh2.aleta_rect())
    # en la T el canto entra en la ranura: el hueco de la pegatina sigue por encima de la cara de la base
    assert gh2.aruco_movil()[1] + gh2.z_canto_movil(gh2.T) >= 0
    assert gh2.pared_iman_aruco_movil() >= 0.8  # plástico entre los imanes del canto y el hueco de la pegatina
    assert gh2.pared_iman_aruco_movil(gh2.X_IMANES_BRIEF) < 0.8  # por eso se movieron de ±50 a ±56


def test_v2_aruco_de_la_base_no_pisa_ranura_tope_ni_cordones():
    base = (-c.LARGO_BASE / 2, -c.ANCHO_BASE / 2, c.LARGO_BASE / 2, c.ANCHO_BASE / 2)
    a = gh2.aruco_base()
    assert gh2.dentro(a, base)
    assert not gh2.solapan(a, gh2.ranura_t_con_chaflan())
    assert not gh2.solapan(a, gh2.tope_esquina())
    for junta in (gh2.T, gh2.ESQ):
        y = c.Y_CORDON[junta]
        assert not gh2.solapan(a, (-c.LARGO_MOVIL / 2, y, c.LARGO_MOVIL / 2, y + c.GROSOR_CHAPA))
        assert not (a[1] <= y <= a[3] and a[0] <= c.LONGITUD_CORDON / 2)


def test_v2_imanes_caben():
    assert gh2.pared_iman_movil() >= 0.8
    assert all(gh2.piel_iman_base(j) >= 0.8 - 1e-9 for j in (gh2.T, gh2.ESQ))
    # los agujeros de la esquina quedan dentro de la base (el tope es macizo hasta la mesa)
    y_max = gh2.y_linea(gh2.ESQ) + gh2.AGUJERO_IMAN_BASE / 2
    assert y_max <= gh2.TOPE_Y[1] - 0.8
    # coaxiales: la línea de imanes de la base coincide con el centro del grosor de la chapa colocada
    assert gh2.y_linea(gh2.T) == pytest.approx(c.Y_CORDON[gh2.T] + c.GROSOR_CHAPA / 2)


def test_v2_polaridad_impide_montarla_al_reves():
    for junta in (gh2.T, gh2.ESQ):
        for dz in (2.0, 5.0, 10.0):
            assert gh2.fuerza_chapa(junta, dz=dz)[2] < 0  # atrae
            assert gh2.fuerza_chapa(junta, dz=dz, girada=True)[2] > 0  # repele


def test_v2_imanes_tiran_desde_10_mm_y_centran():
    peso = gh2.masa_chapa() / 1000 * 9.81
    assert -gh2.fuerza_chapa(gh2.T, dz=10.0)[2] > peso
    for dy in (-5.0, 5.0):  # apoyada en la cara de la base, desplazada: la lleva hacia la ranura
        assert gh2.fuerza_chapa(gh2.T, dz=c.GUIA_T["profundo"], dy=dy)[1] * dy < 0


def test_v2_la_pinza_cabe_al_dejar_la_chapa():
    assert gh2.holgura_dedo_inferior(gh2.T) > 0
    assert gh2.holgura_dedo_inferior(gh2.ESQ) > 0
    assert gh2.APERTURA_PUNTA[1][1] > c.ALETA["grosor"] + 2 * 10  # abierta, ±10 mm de error


def test_v2_base_no_invade_robot_ni_zona_libre_ni_soporte():
    textos = [p.texto for p in gh2.comprobar_mesa()]
    assert not any("invade" in t or "pisa el soporte" in t for t in textos), textos


def test_v2_barrido_de_la_zona_libre():
    # la chapa tumbada (140 × 40) con su centro en la zona del contrato llega a la base: se avisa ...
    area, _ = gh2.solape_barrido_base()
    hay_aviso = any("zona libre" in p.texto for p in gh2.comprobar_mesa())
    assert hay_aviso == (area > 0 or gh2.solape_barrido_base()[1] < gh2.MARGEN_ZONA)
    # ... y la zona propuesta (mismo x y giro) la deja a ≥ MARGEN_ZONA
    area_p, sep_p = gh2.solape_barrido_base(gh2.zona_propuesta())
    assert area_p == 0 and sep_p >= gh2.MARGEN_ZONA - 1e-6


def test_v2_antorcha_en_su_soporte():
    assert gh2.z_punta_en_soporte() >= gh2.PIE_SOPORTE[2] + 1  # el LED no toca el pie
    assert gh2.z_gripperframe_en_soporte() - gh2.z_punta_en_soporte() == pytest.approx(c.LONGITUD_ANTORCHA_ROBOT)
    # la chaveta empieza por debajo del borde del tubo: encaja
    assert gh2.z_punta_en_soporte() + gh2.CHAVETA["z0"] < gh2.TUBO["alto"] - gh2.ENTRADA_CONICA[1]
    # el mango no entra en el tubo
    assert gh2.z_punta_en_soporte() + gh2.largo_cuerpo_antorcha() > gh2.TUBO["alto"]


def test_v2_camaras_y_fov():
    fovs = {n: gh2.fov_necesario(gh2.camara(n, 70.0)) for n in c.CAMARAS_ESTEREO}
    assert all(0 < f < 120 for f in fovs.values())
    for n, f in fovs.items():  # con el FOV justo, todo dentro de la imagen
        cam = gh2.camara(n, f + 0.01)
        for p in gh2.puntos_a_ver():
            u, w, z = cam.proyectar(p)
            assert z > 0 and abs(u) <= 1 and abs(w) <= 1
    # el objetivo de la pose cae en el centro de la imagen
    for n, p in c.CAMARAS_ESTEREO.items():
        u, w, _ = gh2.camara(n, 70.0).proyectar(p["objetivo"])
        assert abs(u) < 1e-6 and abs(w) < 1e-6


def test_v2_brief_coherente_con_el_generador():
    brief = (RAIZ / "hardware" / "v2" / "brief_solidworks.md").read_text(encoding="utf-8")
    assert "contrato.md" in brief
    xs = ", ".join(gh.fmt(x).replace("-", "−") for x in gh2.X_IMANES)
    assert f"X = {xs.replace(', 5', ', +5')}" in brief
    for txt in (f"{gh.fmt(gh2.REBAJE_ARUCO[0])} × {gh.fmt(gh2.REBAJE_ARUCO[0])} × {gh.fmt(gh2.REBAJE_ARUCO[1])}",
                f"Ø {gh.fmt(gh2.AGUJERO_IMAN_MOVIL[0])} × {gh.fmt(gh2.AGUJERO_IMAN_MOVIL[1])}",
                f"Z 0 a **{gh.fmt(gh2.largo_cuerpo_antorcha(), 1)}**", "macizo de Z −6",
                "y {} a {}".format(*(gh.fmt(v).replace("-", "−") for v in gh2.zona_propuesta()["y"]))):
        assert txt in brief, txt
