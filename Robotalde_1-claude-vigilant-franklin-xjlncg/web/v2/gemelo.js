// Gemelo 3D de LeWelder v2 dibujado como un PLANO: aristas blancas, aristas ocultas en discontinuo, caras con un
// sombreado plano muy suave, cotas cian. Lo único con luz y color es el cordón del juez (arco naranja y chispas).
//
// Marco: el de la BASE del contrato (mm). X a lo largo de la base, Y transversal, Z hacia arriba; origen en el centro
// de la cara superior de la base. La cámara es ortográfica (como un plano) y pasa de isométrica a alzado, perfil o
// planta con una animación.
import * as THREE from "three";
import { LineSegments2 } from "./vendor/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "./vendor/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "./vendor/lines/LineMaterial.js";
import * as C from "./contrato.js";

const ANCHO = 1280;
const ALTO = 800;
const COLOR = {
  trazo: 0xeef6ff,
  oculta: 0xa9cbef,
  cian: 0x74d6ff,
  cara: 0x3f86d4,
  arcoBlanco: new THREE.Color(0xfff3dc),
  arco: new THREE.Color(0xff8a1f),
  arcoFrio: new THREE.Color(0xe0661a),
  regular: new THREE.Color(0xd9a13c),
  quemado: new THREE.Color(0x2a0c06),
  rojo: 0xff5148,
};

// Vistas de plano: azimut y elevación de la cámara (grados), alto visible (mm) y centro en la lámina (0-1).
const VISTAS = {
  iso: { az: -125, el: 30 },
  trabajo: { az: -98, el: 30 },
  alzado: { az: -90, el: 0.01 },
  perfil: { az: 180, el: 0.01 },
  planta: { az: -90, el: 89.9 },
};

// Curva fuerte de entrada y salida (cubic-bezier(0.77, 0, 0.175, 1)) para los movimientos de cámara.
function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const fx = (t) => ((ax * t + bx) * t + cx) * t;
  const fy = (t) => ((ay * t + by) * t + cy) * t;
  return (x) => {
    let t = x;
    for (let i = 0; i < 8; i++) {
      const d = (3 * ax * t + 2 * bx) * t + cx;
      if (Math.abs(d) < 1e-6) break;
      t -= (fx(t) - x) / d;
    }
    return fy(Math.min(1, Math.max(0, t)));
  };
}
const easeInOut = bezier(0.77, 0, 0.175, 1);
const easeOut = bezier(0.23, 1, 0.32, 1);
const lerp = (a, b, k) => a + (b - a) * k;
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const reducido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function crearGemelo(lienzo, capaEtiquetas) {
  const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true, alpha: true, preserveDrawingBuffer: false });
  renderer.setClearColor(0x000000, 0);
  const escena = new THREE.Scene();
  const camara = new THREE.OrthographicCamera(-1, 1, 1, -1, -2000, 4000);
  camara.up.set(0, 0, 1);
  escena.add(new THREE.AmbientLight(0xffffff, 1.6));
  const sol = new THREE.DirectionalLight(0xffffff, 1.4);
  sol.position.set(-120, -200, 300);
  escena.add(sol);

  // --- materiales de plano -----------------------------------------------------------------------------------------
  const materialesLinea = [];
  function matLinea({ color = COLOR.trazo, ancho = 2.2, discontinua = false, oculta = false, opacidad = 1,
    raya = 5, hueco = 3.5, siempre = false } = {}) {
    const m = new LineMaterial({ color, linewidth: ancho, dashed: discontinua, dashSize: raya, gapSize: hueco,
      transparent: true, opacity: opacidad, depthWrite: false });
    if (oculta) m.depthFunc = THREE.GreaterDepth;
    if (siempre) m.depthTest = false;
    m.resolution.set(ANCHO, ALTO);
    materialesLinea.push(m);
    return m;
  }
  const matCara = () => new THREE.MeshLambertMaterial({
    color: COLOR.cara, transparent: true, opacity: 0.26, flatShading: true,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1, depthWrite: true,
  });

  /** Una pieza de plano: caras suaves + aristas visibles + aristas ocultas en discontinuo. */
  function pieza(geom, { colorLinea = COLOR.trazo, caras = true } = {}) {
    const grupo = new THREE.Group();
    let mCara = null;
    if (caras) {
      mCara = matCara();
      const malla = new THREE.Mesh(geom, mCara);
      malla.renderOrder = 0;
      grupo.add(malla);
    }
    const lg = new LineSegmentsGeometry().fromEdgesGeometry(new THREE.EdgesGeometry(geom, 25));
    const visible = new LineSegments2(lg, matLinea({ color: colorLinea }));
    visible.renderOrder = 1;
    const oculta = new LineSegments2(lg, matLinea({ color: COLOR.oculta, ancho: 1.3, discontinua: true, oculta: true, opacidad: 0.55 }));
    oculta.computeLineDistances();
    oculta.renderOrder = 2;
    grupo.add(visible, oculta);
    const total = lg.attributes.instanceStart.count;
    return {
      grupo,
      /** Dibuja solo una fracción de las aristas (el plano se "traza"). */
      trazado(f) {
        lg.instanceCount = Math.max(0, Math.round(clamp01(f) * total));
        if (mCara) mCara.opacity = 0.26 * clamp01((f - 0.6) / 0.4);
      },
    };
  }

  function segmentos(puntos, material) {
    const g = new LineSegmentsGeometry();
    g.setPositions(puntos.flat());
    const l = new LineSegments2(g, material);
    if (material.dashed) l.computeLineDistances();
    l.renderOrder = 3;
    return l;
  }
  function ponerSegmentos(linea, puntos) {
    linea.geometry.setPositions(puntos.flat());
    if (linea.material.dashed) linea.computeLineDistances();
  }

  // --- modelo --------------------------------------------------------------------------------------------------
  const modelo = new THREE.Group();
  escena.add(modelo);

  // Base fija 200 x 80 x 6 con su ArUco.
  const gBase = new THREE.BoxGeometry(C.LARGO_BASE, C.ANCHO_BASE, C.GROSOR_CHAPA);
  gBase.translate(0, 0, -C.GROSOR_CHAPA / 2);
  const base = pieza(gBase);
  modelo.add(base.grupo);
  const L = 12.5; // medio lado del ArUco (25 mm)
  const [ax, ay] = [82, -20];
  const aruco = segmentos([
    [ax - L, ay - L, 0.2], [ax + L, ay - L, 0.2], [ax + L, ay - L, 0.2], [ax + L, ay + L, 0.2],
    [ax + L, ay + L, 0.2], [ax - L, ay + L, 0.2], [ax - L, ay + L, 0.2], [ax - L, ay - L, 0.2],
    [ax - 6, ay - 6, 0.2], [ax + 2, ay - 6, 0.2], [ax + 2, ay - 6, 0.2], [ax + 2, ay + 6, 0.2],
    [ax - 6, ay + 2, 0.2], [ax + 6, ay + 2, 0.2],
  ], matLinea({ color: COLOR.oculta, ancho: 1.2 }));
  modelo.add(aruco);
  // Ranura de la T (línea central) y tope interior de la esquina (nervio en el canto +Y), como en el CAD.
  const gTope = new THREE.BoxGeometry(C.LARGO_BASE, C.TOPE_ESQUINA.ancho, C.TOPE_ESQUINA.alto);
  gTope.translate(0, C.ANCHO_BASE / 2 - C.TOPE_ESQUINA.ancho / 2, C.TOPE_ESQUINA.alto / 2);
  const tope = pieza(gTope);
  modelo.add(tope.grupo);
  const yr0 = -(C.GUIA_T.ancho - C.GROSOR_CHAPA) / 2, yr1 = yr0 + C.GUIA_T.ancho, xb = C.LARGO_BASE / 2;
  const ranura = segmentos([[-xb, yr0, 0.2], [xb, yr0, 0.2], [-xb, yr1, 0.2], [xb, yr1, 0.2]],
    matLinea({ color: COLOR.oculta, ancho: 1.2 }));
  modelo.add(ranura);

  // Chapa móvil 140 x 40 x 6 con aleta. Origen local: pie del cordón (canto que apoya, cara -Y), de pie.
  const movil = new THREE.Group();
  const gMovil = new THREE.BoxGeometry(C.LARGO_MOVIL, C.GROSOR_CHAPA, C.ALTO_MOVIL);
  gMovil.translate(0, C.GROSOR_CHAPA / 2, C.ALTO_MOVIL / 2);
  const chapa = pieza(gMovil);
  const gAleta = new THREE.BoxGeometry(C.ALETA.largo, C.ALETA.alto, C.ALETA.grosor);
  gAleta.translate(C.ALETA.x, C.GROSOR_CHAPA + C.ALETA.alto / 2, C.ALTO_MOVIL / 2);
  const aleta = pieza(gAleta);
  movil.add(chapa.grupo, aleta.grupo);
  // Pinza del robot: dos dedos que cogen la aleta por su grosor.
  const pinza = new THREE.Group();
  const matPinza = matLinea({ color: COLOR.cian, ancho: 2 });
  for (const s of [-1, 1]) {
    const z = C.ALTO_MOVIL / 2 + s * (C.ALETA.grosor / 2 + 2.5);
    const x0 = C.ALETA.x - 9, x1 = C.ALETA.x + 9, y0 = C.GROSOR_CHAPA + 6, y1 = C.GROSOR_CHAPA + C.ALETA.alto + 14;
    pinza.add(segmentos([
      [x0, y0, z], [x1, y0, z], [x1, y0, z], [x1, y1, z], [x1, y1, z], [x0, y1, z], [x0, y1, z], [x0, y0, z],
    ], matPinza));
  }
  const palma = C.GROSOR_CHAPA + C.ALETA.alto + 14;
  pinza.add(segmentos([
    [C.ALETA.x - 9, palma, C.ALTO_MOVIL / 2 - 8], [C.ALETA.x - 9, palma, C.ALTO_MOVIL / 2 + 8],
    [C.ALETA.x + 9, palma, C.ALTO_MOVIL / 2 - 8], [C.ALETA.x + 9, palma, C.ALTO_MOVIL / 2 + 8],
    [C.ALETA.x, palma, C.ALTO_MOVIL / 2], [C.ALETA.x, palma + 60, C.ALTO_MOVIL / 2 + 40],
  ], matPinza));
  pinza.visible = false;
  movil.add(pinza);
  modelo.add(movil);

  // Objetivo del plan B: la chapa en su sitio, solo en discontinuo.
  const objetivo = new THREE.Group();
  const lgObj = new LineSegmentsGeometry().fromEdgesGeometry(new THREE.EdgesGeometry(gMovil));
  const lObj = new LineSegments2(lgObj, matLinea({ color: COLOR.cian, ancho: 2, discontinua: true, raya: 6, hueco: 4, siempre: true }));
  lObj.computeLineDistances();
  lObj.renderOrder = 3;
  objetivo.add(lObj);
  objetivo.visible = false;
  modelo.add(objetivo);

  // Cordón: 24 tramos de 5 mm, prisma triangular en la esquina interior (por el lado -Y de la móvil).
  const cordon = new THREE.Group();
  const PIERNA = 5;
  function prisma(x0, x1) {
    const p = [
      [x0, 0, 0], [x0, -PIERNA, 0], [x0, 0, PIERNA],
      [x1, 0, 0], [x1, -PIERNA, 0], [x1, 0, PIERNA],
    ];
    const caras = [[0, 2, 1], [3, 4, 5], [1, 4, 3], [1, 3, 0], [1, 2, 5], [1, 5, 4], [0, 3, 5], [0, 5, 2]];
    const pos = [];
    for (const c of caras) for (const i of c) pos.push(...p[i]);
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    return g;
  }
  const tramos = [];
  for (let i = 0; i < C.N_TRAMOS; i++) {
    const x0 = -C.LONGITUD_CORDON / 2 + i * C.TAMANO_TRAMO;
    const m = new THREE.MeshBasicMaterial({ color: COLOR.arco.clone(), transparent: true, opacity: 1, depthWrite: true });
    const malla = new THREE.Mesh(prisma(x0 + 0.15, x0 + C.TAMANO_TRAMO - 0.15), m);
    malla.visible = false;
    malla.renderOrder = 0;
    cordon.add(malla);
    tramos.push({ malla, calidad: null, desde: 0 });
  }
  // Eje del cordón (dónde va): trazo y punto, como un eje de plano.
  const eje = segmentos([[-C.LONGITUD_CORDON / 2 - 8, -0.6, 0.6], [C.LONGITUD_CORDON / 2 + 8, -0.6, 0.6]],
    matLinea({ color: COLOR.cian, ancho: 1.6, discontinua: true, raya: 10, hueco: 3, siempre: true }));
  eje.visible = false;
  cordon.add(eje);
  // Fantasma del robot: línea discontinua de cota a lo largo del cordón.
  const lFantasma = segmentos([[0, 0, 0], [0, 0, 0]],
    matLinea({ color: COLOR.cian, ancho: 3, discontinua: true, raya: 4, hueco: 3, siempre: true }));
  lFantasma.visible = false;
  cordon.add(lFantasma);
  const marcaFantasma = segmentos([[0, 0, 0], [0, 0, 0]], matLinea({ color: COLOR.cian, ancho: 2, siempre: true }));
  marcaFantasma.visible = false;
  cordon.add(marcaFantasma);
  modelo.add(cordon);

  // --- antorchas ---------------------------------------------------------------------------------------------------
  function antorcha(color, discontinua = false) {
    const g = new THREE.Group();
    const cono = new THREE.ConeGeometry(4.5, 14, 10, 1, true);
    cono.rotateX(Math.PI);
    cono.translate(0, 7, 0);
    const cuerpo = new THREE.CylinderGeometry(7, 7, 70, 10, 1, true);
    cuerpo.translate(0, 14 + 35, 0);
    const m = matLinea({ color, ancho: 1.8, discontinua, siempre: true });
    for (const geo of [cono, cuerpo]) {
      const l = new LineSegments2(new LineSegmentsGeometry().fromEdgesGeometry(new THREE.EdgesGeometry(geo, 1)), m);
      if (discontinua) l.computeLineDistances();
      l.renderOrder = 3;
      g.add(l);
    }
    // eje de la antorcha (línea de trazo y punto)
    g.add(segmentos([[0, -4, 0], [0, 100, 0]], matLinea({ color, ancho: 1, discontinua: true, raya: 8, hueco: 3, siempre: true })));
    // Ángulo de trabajo 45° (bisectriz de la esquina, hacia -Y y arriba) y 10° de empuje (mango detrás, en -X).
    const dir = new THREE.Vector3(-Math.sin(THREE.MathUtils.degToRad(10)), -0.7071, 0.7071).normalize();
    g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    g.visible = false;
    cordon.add(g);
    return g;
  }
  const antorchaJuez = antorcha(COLOR.trazo);
  const antorchaRobot = antorcha(COLOR.cian, true);

  // Brillo del arco: sprite con degradado radial (aditivo).
  function texturaBrillo() {
    const c = document.createElement("canvas");
    c.width = c.height = 128;
    const x = c.getContext("2d");
    const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, "rgba(255,250,235,1)");
    g.addColorStop(0.18, "rgba(255,214,140,0.9)");
    g.addColorStop(0.45, "rgba(255,138,31,0.35)");
    g.addColorStop(1, "rgba(255,138,31,0)");
    x.fillStyle = g;
    x.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  }
  const brillo = new THREE.Sprite(new THREE.SpriteMaterial({ map: texturaBrillo(), blending: THREE.AdditiveBlending,
    depthTest: false, depthWrite: false, transparent: true }));
  brillo.renderOrder = 5;
  brillo.visible = false;
  cordon.add(brillo);

  // Chispas: partículas aditivas con gravedad.
  const N_CHISPAS = 360;
  const pos = new Float32Array(N_CHISPAS * 3);
  const col = new Float32Array(N_CHISPAS * 3);
  const vel = new Float32Array(N_CHISPAS * 3);
  const vida = new Float32Array(N_CHISPAS);
  for (let i = 0; i < N_CHISPAS; i++) pos[i * 3 + 2] = -1e5;
  const gChispas = new THREE.BufferGeometry();
  gChispas.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  gChispas.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const chispas = new THREE.Points(gChispas, new THREE.PointsMaterial({ size: 4, sizeAttenuation: false, vertexColors: true,
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false }));
  chispas.renderOrder = 6;
  chispas.frustumCulled = false;
  cordon.add(chispas);
  let siguienteChispa = 0;
  let ritmoChispas = 0; // chispas por segundo
  const origenChispas = new THREE.Vector3();

  function emitir(n) {
    for (let k = 0; k < n; k++) {
      const i = siguienteChispa;
      siguienteChispa = (siguienteChispa + 1) % N_CHISPAS;
      pos[i * 3] = origenChispas.x; pos[i * 3 + 1] = origenChispas.y; pos[i * 3 + 2] = origenChispas.z;
      const a = Math.random() * Math.PI * 2;
      const v = 60 + Math.random() * 170;
      const sube = 0.5 + Math.random() * 0.9;
      vel[i * 3] = Math.cos(a) * v;
      vel[i * 3 + 1] = Math.sin(a) * v * 0.8 - 60;
      vel[i * 3 + 2] = sube * v;
      vida[i] = 0.18 + Math.random() * 0.4;
    }
  }
  function moverChispas(dt) {
    if (ritmoChispas > 0) {
      const n = ritmoChispas * dt;
      emitir(Math.floor(n) + (Math.random() < n % 1 ? 1 : 0));
    }
    for (let i = 0; i < N_CHISPAS; i++) {
      // muertas: fuera de la vista (en un lienzo con alfa, un punto negro aditivo se ve negro)
      if (vida[i] <= 0) { pos[i * 3 + 2] = -1e5; col[i * 3] = col[i * 3 + 1] = col[i * 3 + 2] = 0; continue; }
      vida[i] -= dt;
      vel[i * 3 + 2] -= 900 * dt;
      pos[i * 3] += vel[i * 3] * dt; pos[i * 3 + 1] += vel[i * 3 + 1] * dt; pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
      if (pos[i * 3 + 2] < 0) { pos[i * 3 + 2] = 0; vel[i * 3 + 2] *= -0.3; }
      const k = clamp01(vida[i] / 0.5);
      col[i * 3] = 1; col[i * 3 + 1] = 0.45 + 0.5 * k; col[i * 3 + 2] = 0.15 + 0.6 * k * k;
      col[i * 3] *= k + 0.2; col[i * 3 + 1] *= k + 0.1; col[i * 3 + 2] *= k;
    }
    gChispas.attributes.position.needsUpdate = true;
    gChispas.attributes.color.needsUpdate = true;
  }

  // --- cotas ---------------------------------------------------------------------------------------------------
  const etiquetas = []; // {el, punto: Vector3, objeto?: Object3D (si es relativo a él), visible}
  function etiqueta(texto, clase = "") {
    const el = document.createElement("span");
    el.className = `etq3d ${clase}`.trim();
    el.textContent = texto;
    el.style.opacity = "0";
    capaEtiquetas.append(el);
    const e = { el, punto: new THREE.Vector3(), objeto: null, visible: false };
    etiquetas.push(e);
    return e;
  }

  const matCota = matLinea({ color: COLOR.cian, ancho: 1.5, siempre: true });
  /** Cota de a a b, desplazada `dir * sep`, con flechas y texto. Se dibuja creciendo desde el centro. */
  function cota(a, b, dir, sep, texto, clase = "") {
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), D = new THREE.Vector3(...dir).normalize();
    const linea = segmentos([[0, 0, 0], [0, 0, 0]], matCota);
    linea.visible = false;
    modelo.add(linea);
    const e = etiqueta(texto, clase);
    const c = { k: 0, objetivo: 0, linea, e, A, B, D, sep };
    c.dibujar = () => {
      const k = easeOut(c.k);
      const a2 = c.A.clone().addScaledVector(c.D, c.sep), b2 = c.B.clone().addScaledVector(c.D, c.sep);
      const m = a2.clone().lerp(b2, 0.5);
      const pa = m.clone().lerp(a2, k), pb = m.clone().lerp(b2, k);
      const u = b2.clone().sub(a2).normalize();
      const s = 6;
      const ext = (p, q) => [p.clone().addScaledVector(c.D, 2).toArray(), q.clone().addScaledVector(c.D, 4).toArray()];
      const flecha = (p, sentido) => {
        const atras = p.clone().addScaledVector(u, -s * sentido);
        return [
          [p.toArray(), atras.clone().addScaledVector(c.D, s * 0.32).toArray()],
          [p.toArray(), atras.clone().addScaledVector(c.D, -s * 0.32).toArray()],
        ];
      };
      const segs = [[pa.toArray(), pb.toArray()]];
      if (k > 0.02) segs.push(...(c.sep ? [ext(c.A, a2), ext(c.B, b2)] : []), ...flecha(pa, -1), ...flecha(pb, 1));
      ponerSegmentos(c.linea, segs.flat());
      c.e.punto.copy(m);
      c.linea.visible = c.k > 0.001;
      c.e.visible = c.k > 0.6;
    };
    return c;
  }
  const H = C.LONGITUD_CORDON / 2;
  const cotas = {
    base: cota([-C.LARGO_BASE / 2, -C.ANCHO_BASE / 2, 0], [C.LARGO_BASE / 2, -C.ANCHO_BASE / 2, 0], [0, -1, 0], 26, "200"),
    ancho: cota([C.LARGO_BASE / 2, -C.ANCHO_BASE / 2, 0], [C.LARGO_BASE / 2, C.ANCHO_BASE / 2, 0], [1, 0, 0], 22, "80"),
    cordon: cota([-H, 0, 0], [H, 0, 0], [0, -1, 0], 14, "cordón 120 · 24 × 5", "blanca"),
    alto: cota([-C.LARGO_MOVIL / 2, 0, 0], [-C.LARGO_MOVIL / 2, 0, C.ALTO_MOVIL], [-1, 0, 0], 16, "40"),
  };
  // La cota del cordón y la de la altura van con la chapa móvil (Y del cordón): se recolocan en `junta()`.
  // Cota viva de la carrera: entre la punta del juez y el fantasma.
  const cotaCarrera = cota([0, 0, 0], [1, 0, 0], [0, 0, 1], 0, "", "grande");
  cotaCarrera.k = 1;

  // Etiquetas sueltas
  const etqFantasma = etiqueta("ROBOT", "robot");
  const etqJuez = etiqueta("TÚ", "juez");
  const etqChapa = etiqueta("CHAPA SUELTA 140 × 40 × 6", "blanca");
  etqFantasma.objeto = cordon;
  etqJuez.objeto = cordon;

  // --- estado ------------------------------------------------------------------------------------------------------
  let tipo = "esquina";
  let yCordon = C.Y_CORDON.esquina;
  const estado = {
    trazo: { desde: 0, dur: 0, f: 1 },
    montaje: { actual: 1, objetivo: 1 },
    juez: null,
    robotX: null,
    fantasmaX: null,
    carrera: false,
    atraccion: false,
    tAtr: 0,
  };

  function junta(t) {
    tipo = t === "t" ? "t" : "esquina";
    yCordon = C.Y_CORDON[tipo];
    cordon.position.set(0, yCordon, 0);
    objetivo.position.set(0, yCordon, 0);
    for (const nombre of ["cordon", "alto"]) {
      const c = cotas[nombre];
      c.A.y = c.B.y = yCordon;
      c.dibujar();
    }
    if (estado.montaje.actual >= 1) colocarMovil(1);
  }

  // Poses de la chapa móvil durante el montaje: tumbada en la zona libre → levantada → girada → encajada.
  const qTumbada = new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2, 0, THREE.MathUtils.degToRad(24), "ZYX"));
  const qDePie = new THREE.Quaternion();
  let montajeCae = false;
  function colocarMovil(p) {
    const zFin = C.Z_CANTO_MOVIL[tipo];
    // zona libre del contrato pasada al marco de la base (≈ X -200), sobre la mesa (Z = -6);
    // en la atracción la chapa baja desde arriba (para no salirse del encuadre).
    const k0 = montajeCae ? { pos: new THREE.Vector3(0, yCordon - 30, 150), q: qDePie }
      : { pos: new THREE.Vector3(-205, -10, -C.GROSOR_CHAPA), q: qTumbada };
    const k1 = montajeCae ? { pos: new THREE.Vector3(0, yCordon - 20, 110), q: qDePie }
      : { pos: new THREE.Vector3(-205, -10, 70), q: qTumbada };
    const k2 = montajeCae ? { pos: new THREE.Vector3(0, yCordon - 4, 40), q: qDePie }
      : { pos: new THREE.Vector3(-40, yCordon - 10, 80), q: qDePie };
    const k3 = { pos: new THREE.Vector3(0, yCordon, zFin), q: qDePie };
    let a, b, k;
    if (p < 0.2) { a = k0; b = k0; k = 0; }
    else if (p < 0.45) { a = k0; b = k1; k = (p - 0.2) / 0.25; }
    else if (p < 0.75) { a = k1; b = k2; k = (p - 0.45) / 0.3; }
    else { a = k2; b = k3; k = (p - 0.75) / 0.25; }
    k = easeInOut(clamp01(k));
    movil.position.lerpVectors(a.pos, b.pos, k);
    movil.quaternion.slerpQuaternions(a.q, b.q, k);
    pinza.visible = p > 0.2 && p < 0.995;
    etqChapa.visible = p < 0.2 && !montajeCae;
    etqChapa.punto.copy(movil.position).add(new THREE.Vector3(0, -50, 0));
  }

  function trazar(dur = 1.6) {
    if (reducido()) dur = 0.01;
    estado.trazo = { desde: performance.now(), dur: dur * 1000, f: 0 };
  }

  function cordonVacio() {
    for (const t of tramos) { t.calidad = null; t.malla.visible = false; }
  }
  function pintar(i, calidad) {
    const t = tramos[i];
    if (!t || t.calidad === calidad) return;
    t.calidad = calidad;
    t.desde = performance.now();
    t.malla.visible = calidad && calidad !== "suelto";
  }
  function colorTramo(t, ahora) {
    const m = t.malla.material;
    if (t.calidad === "bien") {
      const k = clamp01((ahora - t.desde) / 1400);
      if (k < 0.35) m.color.copy(COLOR.arcoBlanco).lerp(COLOR.arco, k / 0.35);
      else m.color.copy(COLOR.arco).lerp(COLOR.arcoFrio, (k - 0.35) / 0.65);
    } else if (t.calidad === "regular") m.color.copy(COLOR.regular);
    else if (t.calidad === "quemado") m.color.copy(COLOR.quemado);
    else if (t.calidad === "guia") m.color.set(COLOR.cian);
    m.opacity = t.calidad === "guia" ? 0.55 : 1;
  }

  // --- cámara --------------------------------------------------------------------------------------------------
  const cam = { az: -125, el: 30, alto: 330, cx: 0.66, cy: 0.5, giro: 0 };
  let tween = null;
  function vista(nombre, { alto = cam.alto, centro = [cam.cx, cam.cy], giro = 0, dur = 1.1 } = {}) {
    const v = VISTAS[nombre] || VISTAS.iso;
    let az0 = ((cam.az % 360) + 540) % 360 - 180;
    let az1 = v.az;
    if (az1 - az0 > 180) az1 -= 360;
    if (az0 - az1 > 180) az1 += 360;
    const desde = { az: az0, el: cam.el, alto: cam.alto, cx: cam.cx, cy: cam.cy };
    const hasta = { az: az1, el: v.el, alto, cx: centro[0], cy: centro[1] };
    cam.giro = giro;
    if (reducido() || dur <= 0) { Object.assign(cam, hasta); tween = null; return; }
    tween = { desde, hasta, t0: performance.now(), dur: dur * 1000 };
  }
  function colocarCamara() {
    const az = THREE.MathUtils.degToRad(cam.az), el = THREE.MathUtils.degToRad(cam.el);
    const objetivoCam = new THREE.Vector3(0, 10, 10);
    const d = new THREE.Vector3(Math.cos(el) * Math.cos(az), Math.cos(el) * Math.sin(az), Math.sin(el));
    camara.position.copy(objetivoCam).addScaledVector(d, 1000);
    camara.lookAt(objetivoCam);
    const h = cam.alto, w = h * ANCHO / ALTO;
    camara.left = -cam.cx * w; camara.right = (1 - cam.cx) * w;
    camara.top = cam.cy * h; camara.bottom = -(1 - cam.cy) * h;
    camara.updateProjectionMatrix();
  }

  // --- tamaño --------------------------------------------------------------------------------------------------
  function ajustar(escala = 1) {
    renderer.setPixelRatio(Math.min(2, (window.devicePixelRatio || 1) * escala));
    renderer.setSize(ANCHO, ALTO, false);
  }
  ajustar();

  const v3 = new THREE.Vector3();
  function aPantalla(p, objeto = null) {
    v3.copy(p);
    if (objeto) v3.applyMatrix4(objeto.matrixWorld);
    v3.project(camara);
    return { x: (v3.x + 1) / 2 * ANCHO, y: (1 - v3.y) / 2 * ALTO, z: v3.z };
  }

  // --- atracción: el robot monta y suelda solo, en bucle ---------------------------------------------------------
  function pasoAtraccion(dt) {
    estado.tAtr += dt;
    const t = estado.tAtr;
    if (t < 0.05 && !estado.atrIniciada) {
      estado.atrIniciada = true;
      cordonVacio();
      colocarMovil(0);
      estado.montaje.actual = estado.montaje.objetivo = 0;
      trazar(1.6);
    }
    if (t >= 1.6 && t < 5.6) estado.montaje.objetivo = (t - 1.6) / 4;
    if (t >= 5.6) estado.montaje.objetivo = 1;
    if (t >= 6.2 && t < 13.2) {
      const x = (t - 6.2) / 7 * C.LONGITUD_CORDON;
      estado.robotX = x;
      const i = Math.min(C.N_TRAMOS - 1, Math.floor(x / C.TAMANO_TRAMO));
      for (let j = 0; j < i; j++) if (!tramos[j].calidad) pintar(j, "bien");
      ritmoChispas = 150;
      origenChispas.set(C.xCordonABase(x), 0, 1);
    } else {
      if (t >= 13.2 && tramos[C.N_TRAMOS - 1].calidad !== "bien") for (let j = 0; j < C.N_TRAMOS; j++) pintar(j, "bien");
      estado.robotX = null;
      ritmoChispas = 0;
    }
    if (t > 16.5) {
      estado.tAtr = 0;
      estado.atrIniciada = false;
      junta(tipo === "t" ? "esquina" : "t");
    }
  }

  // --- bucle ---------------------------------------------------------------------------------------------------
  let ultimo = performance.now();
  let activo = true;
  function cuadro(ahora) {
    const dt = Math.min(0.05, (ahora - ultimo) / 1000);
    ultimo = ahora;

    if (tween) {
      const k = clamp01((ahora - tween.t0) / tween.dur);
      const e = easeInOut(k);
      for (const p of ["az", "el", "alto", "cx", "cy"]) cam[p] = lerp(tween.desde[p], tween.hasta[p], e);
      if (k >= 1) tween = null;
    }
    if (cam.giro && !reducido()) cam.az += cam.giro * dt;
    colocarCamara();

    if (estado.atraccion) pasoAtraccion(dt);

    // trazado de las aristas
    const tr = estado.trazo;
    if (tr.f < 1) {
      tr.f = clamp01((ahora - tr.desde) / Math.max(1, tr.dur));
      base.trazado(tr.f);
      tope.trazado(tr.f);
      chapa.trazado(clamp01(tr.f * 1.3 - 0.3));
      aleta.trazado(clamp01(tr.f * 1.6 - 0.6));
    }

    // montaje: la pose sigue al progreso recibido sin saltos
    const m = estado.montaje;
    if (Math.abs(m.objetivo - m.actual) > 1e-4) {
      m.actual += (m.objetivo - m.actual) * (1 - Math.exp(-dt * 6));
      if (Math.abs(m.objetivo - m.actual) < 0.002) m.actual = m.objetivo;
      colocarMovil(m.actual);
    }

    for (const t of tramos) if (t.malla.visible) colorTramo(t, ahora);

    // punta del juez
    const j = estado.juez;
    if (j && j.visible) {
      const px = C.xCordonABase(j.x), py = j.y || 0, pz = Math.max(0, j.z || 0) + 1;
      antorchaJuez.position.set(px, py, pz);
      antorchaJuez.visible = true;
      const arco = j.gatillo && j.apoyada && j.calidad !== "suelto";
      brillo.visible = arco;
      if (arco) {
        const s = 34 + Math.random() * 14 + (j.calidad === "quemado" ? 20 : 0);
        brillo.scale.set(s, s, 1);
        brillo.position.set(px, py, pz);
        brillo.material.color.set(j.calidad === "quemado" ? 0xff5a2a : 0xffffff);
      }
      ritmoChispas = arco ? (j.calidad === "bien" ? 320 : j.calidad === "regular" ? 140 : 60) : 0;
      origenChispas.set(px, py - 1, pz);
      etqJuez.visible = true;
      etqJuez.punto.set(px, -40, -2);
    } else if (!estado.atraccion) {
      antorchaJuez.visible = false;
      brillo.visible = false;
      etqJuez.visible = false;
      if (!estado.robotX) ritmoChispas = 0;
    } else {
      antorchaJuez.visible = false;
      etqJuez.visible = false;
    }

    // antorcha del robot (demostración y atracción)
    if (estado.robotX != null) {
      antorchaRobot.visible = true;
      antorchaRobot.position.set(C.xCordonABase(estado.robotX), 0, 1);
      if (!estado.atraccion && estado.robotSuelda) {
        brillo.visible = true;
        const s = 30 + Math.random() * 10;
        brillo.scale.set(s, s, 1);
        brillo.position.set(C.xCordonABase(estado.robotX), 0, 1);
        brillo.material.color.set(0xffffff);
        ritmoChispas = 150;
        origenChispas.set(C.xCordonABase(estado.robotX), -1, 1);
      } else if (estado.atraccion) {
        brillo.visible = true;
        brillo.scale.set(32, 32, 1);
        brillo.position.set(C.xCordonABase(estado.robotX), 0, 1);
      }
    } else {
      antorchaRobot.visible = false;
      if (estado.atraccion) brillo.visible = false;
    }

    // fantasma
    if (estado.fantasmaX != null) {
      const xf = C.xCordonABase(Math.min(C.LONGITUD_CORDON, Math.max(0, estado.fantasmaX)));
      lFantasma.visible = true;
      ponerSegmentos(lFantasma, [[-H, -2, 7], [xf, -2, 7]]);
      marcaFantasma.visible = true;
      ponerSegmentos(marcaFantasma, [[xf, -2, 0], [xf, -2, 32], [xf - 4, -2, 32], [xf + 4, -2, 32]]);
      etqFantasma.visible = estado.carrera || estado.etqFantasma;
      etqFantasma.punto.set(xf, -2, 40);
    } else {
      lFantasma.visible = marcaFantasma.visible = false;
      etqFantasma.visible = false;
    }

    // cota viva de la carrera
    if (estado.carrera && j && j.visible && estado.fantasmaX != null) {
      const xa = C.xCordonABase(j.x), xb = C.xCordonABase(Math.max(0, Math.min(C.LONGITUD_CORDON, estado.fantasmaX)));
      const d = j.x - estado.fantasmaX;
      if (Math.abs(d) > 1.5) {
        cotaCarrera.A.set(Math.min(xa, xb), yCordon - 2, 46);
        cotaCarrera.B.set(Math.max(xa, xb), yCordon - 2, 46);
        cotaCarrera.dibujar();
        cotaCarrera.e.el.textContent = `Δ ${Math.abs(d).toFixed(0)} mm`;
        cotaCarrera.e.el.className = `etq3d grande ${d >= 0 ? "juez" : "robot"}`;
        cotaCarrera.e.visible = true;
        cotaCarrera.e.punto.z += 16;
      } else {
        cotaCarrera.linea.visible = false;
        cotaCarrera.e.visible = false;
      }
    } else {
      cotaCarrera.linea.visible = false;
      cotaCarrera.e.visible = false;
    }

    // cotas fijas: crecen o se recogen
    for (const c of Object.values(cotas)) {
      if (c.k !== c.objetivo) {
        c.k = reducido() ? c.objetivo : c.objetivo > c.k ? Math.min(c.objetivo, c.k + dt / 0.45) : Math.max(c.objetivo, c.k - dt / 0.2);
        c.dibujar();
      }
    }

    moverChispas(dt);
    modelo.updateMatrixWorld(true);
    renderer.render(escena, camara);

    // etiquetas HTML
    for (const e of etiquetas) {
      const vis = e.visible && modelo.visible;
      e.el.style.opacity = vis ? "1" : "0";
      if (!vis) continue;
      const p = aPantalla(e.punto, e.objeto);
      e.el.style.translate = `${p.x.toFixed(1)}px ${p.y.toFixed(1)}px`;
    }
    if (activo) requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);

  // --- API -----------------------------------------------------------------------------------------------------
  junta("esquina");
  colocarMovil(1);
  return {
    vista,
    junta,
    get tipo() { return tipo; },
    trazar,
    ajustar,
    visible(v) { modelo.visible = v; },
    /** Progreso del montaje (0 = chapa tumbada en la zona libre, 1 = encajada). */
    montaje(p, { inmediato = false } = {}) {
      estado.montaje.objetivo = clamp01(p);
      if (inmediato) { estado.montaje.actual = estado.montaje.objetivo; colocarMovil(estado.montaje.actual); }
    },
    cordonVacio,
    pintar,
    pintarTodo(lista) { lista.forEach((c, i) => pintar(i, c)); },
    /** Punta de la antorcha del juez (marco del cordón: x 0-120, y desvío, z altura) o null. */
    punta(m) { estado.juez = m ? { ...m, visible: true } : null; },
    /** Antorcha del robot sobre el cordón (x 0-120) o null; `suelda` enciende el arco. */
    antorchaRobot(x, suelda = false) { estado.robotX = x; estado.robotSuelda = suelda; },
    fantasma(x, { etiqueta: conEtq = false } = {}) { estado.fantasmaX = x; estado.etqFantasma = conEtq; },
    carrera(v) { estado.carrera = v; },
    cotas(nombres) {
      for (const [n, c] of Object.entries(cotas)) c.objetivo = nombres.includes(n) ? 1 : 0;
    },
    ejeCordon(v) { eje.visible = v; },
    objetivoPlanB(v) { objetivo.visible = v; },
    atraccion(v) {
      if (v === estado.atraccion) return;
      estado.atraccion = v;
      estado.tAtr = 0;
      estado.atrIniciada = false;
      montajeCae = v;
      if (!v) { estado.robotX = null; ritmoChispas = 0; }
    },
    /** Posición en la lámina (px) de un punto del cordón (x 0-120). */
    puntoCordon(x = C.LONGITUD_CORDON / 2) {
      modelo.updateMatrixWorld(true);
      return aPantalla(new THREE.Vector3(C.xCordonABase(x), yCordon, 2));
    },
    parar() { activo = false; },
  };
}
