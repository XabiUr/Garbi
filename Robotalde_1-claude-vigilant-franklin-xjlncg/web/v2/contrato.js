// Medidas compartidas de LeWelder v2 para la tablet.
//
// COPIADAS A MANO de `lewelder/contrato.py` (sección v2 · escuela-taller). Si cambian allí, se cambian aquí.
// Unidades: milímetros, segundos y grados.
//
// Marco de la BASE: origen en el centro de la cara superior de la chapa base, X a lo largo del lado largo,
// Y transversal, Z hacia arriba. El cordón va de X = -LONGITUD_CORDON/2 a +LONGITUD_CORDON/2 en Z = 0, en
// Y = Y_CORDON[junta], por el lado -Y de la chapa móvil (el que miran las webcams). La aleta va por el +Y.

export const LONGITUD_CORDON = 120.0; // contrato.py: LONGITUD_CORDON
export const TAMANO_TRAMO = 5.0; // contrato.py: TAMANO_TRAMO
export const N_TRAMOS = LONGITUD_CORDON / TAMANO_TRAMO; // 24

export const LARGO_BASE = 200.0; // contrato.py: LARGO_BASE
export const ANCHO_BASE = 80.0; // contrato.py: ANCHO_BASE
export const GROSOR_CHAPA = 6.0; // contrato.py: GROSOR_CHAPA (base y móvil)
export const LARGO_MOVIL = 140.0; // contrato.py: LARGO_MOVIL
export const ALTO_MOVIL = 40.0; // contrato.py: ALTO_MOVIL (altura de la móvil de pie)
// contrato.py: ALETA (x: centro de la aleta respecto al de la chapa)
export const ALETA = { largo: 40.0, alto: 18.0, grosor: 5.0, x: -35.0 };
export const GUIA_T = { ancho: GROSOR_CHAPA + 1.0, profundo: 2.0 }; // contrato.py: GUIA_T
// contrato.py: TOPE_ESQUINA (nervio dentro de la base, en el canto +Y: Y 37 a 40)
export const TOPE_ESQUINA = { alto: 3.0, ancho: 3.0 };

// contrato.py: Y_CORDON = {T: 0.0, ESQUINA: ANCHO_BASE / 2 - TOPE_ESQUINA["ancho"] - GROSOR_CHAPA}  (0 y 31)
export const Y_CORDON = { t: 0.0, esquina: ANCHO_BASE / 2 - TOPE_ESQUINA.ancho - GROSOR_CHAPA };
// contrato.py: Z_CANTO_MOVIL (en la T la chapa móvil entra 2 mm en la ranura)
export const Z_CANTO_MOVIL = { t: -2.0, esquina: 0.0 };

// contrato.py: ANGULO_TRABAJO_OBJETIVO["t"] y ["esquina"] (la esquina se suelda por dentro)
export const ANGULO_TRABAJO_OBJETIVO = { t: 45.0, esquina: 45.0 };
export const ANGULO_AVANCE_RANGO = [0.0, 20.0]; // contrato.py: ANGULO_AVANCE_RANGO
export const VELOCIDAD_OBJETIVO = [4.0, 6.0]; // contrato.py: VELOCIDAD_OBJETIVO (mm/s)
export const ALTURA_APOYO = 2.0; // contrato.py: ALTURA_APOYO (mm)

// contrato.py: POSICIONES_SOLDEO (ISO 6947)
export const POSICIONES_SOLDEO = {
  PA: "plana",
  PB: "horizontal en ángulo",
  PC: "horizontal (cornisa)",
  PD: "en ángulo bajo techo",
  PE: "bajo techo",
  PF: "vertical ascendente",
  PG: "vertical descendente",
};

// contrato.py: ORDENES (orden → nivel de la escalera de alcance)
export const ORDENES = {
  "monta una unión en T": 1,
  "monta una unión en esquina": 1,
  "señala el cordón": 1,
  "coge la antorcha y suelda la junta": 1,
  "desmonta la junta": 2,
  "acércame la antorcha": 2,
  "gira la junta hacia ti": 3,
};

// contrato.py: NOMBRE_JUNTA
export const NOMBRE_JUNTA = { t: "en T", esquina: "en esquina" };

/** Centro del tramo i (0..23) en X del marco de la base. */
export function xTramo(i) {
  return -LONGITUD_CORDON / 2 + (i + 0.5) * TAMANO_TRAMO;
}

/** Posición x del cordón (0..120, sentido de avance) → X del marco de la base. */
export function xCordonABase(x) {
  return x - LONGITUD_CORDON / 2;
}
