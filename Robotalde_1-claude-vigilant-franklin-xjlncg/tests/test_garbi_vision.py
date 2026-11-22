"""Visión anterior de Garbi (`garbi.vision`, con ArUco).

La escena ya no tiene ArUco (especificación técnica del 19-11: «sin ArUco»): la cámara se calibra con las esquinas del
tapete y la madera se ve por su vinilo negro. Las pruebas de la visión con ArUco (calibrar con los marcadores del tapete,
la tabla por sus 2 marcadores, la viruta y el apunto con la cámara del robot) se sustituyen por las de
`tests/test_garbi_percepcion.py` (`garbi.percepcion`), que miden lo mismo contra la verdad de la simulación. Aquí queda
lo que no depende de los marcadores.
"""
import numpy as np

from garbi import vision as v


def test_ajuste_rigido_2d_recupera_giro_y_traslacion():
    loc = v.esquinas_locales((-46, 26), 18)
    giro = np.radians(17.0)
    R = np.array([[np.cos(giro), -np.sin(giro)], [np.sin(giro), np.cos(giro)]])
    mesa = loc @ R.T + [160.0, -12.0]
    t, gr = v.ajuste_rigido_2d(loc, mesa)
    assert np.allclose(t, [160, -12], atol=1e-6) and abs(gr - 17.0) < 1e-6
