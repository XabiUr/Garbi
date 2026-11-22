from lewelder import contrato as c


def test_tramos():
    assert c.N_TRAMOS == 24
    assert c.N_TRAMOS * c.TAMANO_TRAMO == c.LONGITUD_CORDON


def test_ids_aruco_no_se_solapan():
    ids_pieza = set(c.IDS_PIEZA[c.TipoPieza.RECTA]) | set(c.IDS_PIEZA[c.TipoPieza.T])
    assert not ids_pieza & set(c.IDS_ANCLAJE)
    assert c.tipo_por_id(12) is c.TipoPieza.RECTA
    assert c.tipo_por_id(25) is c.TipoPieza.T
    assert c.tipo_por_id(3) is None


def test_instrucciones():
    assert c.instruccion_soldar(c.TipoPieza.T, "B") == "suelda la unión en T del anclaje B"
    assert c.instruccion_soldar("recta", "A") == "suelda la unión recta del anclaje A"
    assert c.instruccion_colocar("C") == "coloca la pieza en el anclaje C"


# --- v2 ----------------------------------------------------------------------------------------------------------
def test_v2_cordon_y_chapa_movil_caben_en_la_base():
    # el cordón cabe a lo largo de la base y la chapa móvil también
    assert c.LONGITUD_CORDON < c.LARGO_MOVIL <= c.LARGO_BASE
    for junta, y in c.Y_CORDON.items():
        assert -c.ANCHO_BASE / 2 <= y <= c.ANCHO_BASE / 2 - c.GROSOR_CHAPA, junta


def test_v2_aruco_de_la_base_no_lo_tapa_la_chapa_ni_el_cordon():
    x, y, _ = c.ARUCO_EN_BASE
    medio = c.LADO_ARUCO_V2 / 2 + c.MARGEN_BLANCO_ARUCO
    assert x - medio > c.LONGITUD_CORDON / 2  # fuera del cordón (y de la chapa móvil, que va sobre él)
    assert x + medio <= c.LARGO_BASE / 2
    assert -c.ANCHO_BASE / 2 <= y - medio and y + medio < min(c.Y_CORDON.values())  # en el lado -Y, libre


def test_v2_aruco_y_aleta_de_la_movil_no_se_pisan():
    medio = c.LADO_ARUCO_V2 / 2 + c.MARGEN_BLANCO_ARUCO
    x_aruco = c.ARUCO_EN_MOVIL[0]
    assert abs(x_aruco - c.ALETA["x"]) > medio + c.ALETA["largo"] / 2
    assert abs(x_aruco) + medio <= c.LARGO_MOVIL / 2
    assert c.ARUCO_EN_MOVIL[1] + medio <= c.ALTO_MOVIL + 1e-9


def test_v2_ids_aruco_distintos_de_v1():
    ids_v2 = {c.ID_BASE, *c.IDS_MOVIL.values()}
    ids_v1 = set(c.IDS_ANCLAJE) | set(c.IDS_PIEZA[c.TipoPieza.RECTA]) | set(c.IDS_PIEZA[c.TipoPieza.T])
    assert not ids_v2 & ids_v1


def test_v2_vocabulario():
    assert c.orden_montar(c.TipoJunta.T) in c.ORDENES
    assert c.orden_montar("esquina") == "monta una unión en esquina"
    assert sorted(o for o, n in c.ORDENES.items() if n == 1)  # hay núcleo
    assert c.ANGULO_TRABAJO_OBJETIVO["esquina"] == 45.0
