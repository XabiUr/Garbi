// LeWelder · tablet. Gemelo 3D de la pieza (three.js), nota, avisos, robot y certificado.
// Habla con el servidor por WebSocket (protocolo en lewelder/servidor.py). Sin dependencias de internet.
import * as THREE from "./vendor/three-0.170.0.module.min.js";

const $ = (id) => document.getElementById(id);
const COLORES = { bien: 0x3ddc84, regular: 0xffb020, quemado: 0xff4d4f, fuera: 0x9aa4b2, robot: 0x38bdf8 };
const NOMBRE_MODO = {
  espera: "En espera", examen: "Examen en curso", nota: "Nota del examen", repaso: "Repaso del robot",
  certificado: "Certificado", maestro: "El robot suelda",
};
const NOMBRE_NIVEL = { aprendiz: "Aprendiz", oficial: "Oficial", maestro: "Maestro" };
const NOMBRE_POLITICA = { vla: "VLA", act: "ACT", replay: "Replay" };

let C = null;            // contrato (/api/contrato)
let E = { modo: "espera", nivel: "oficial", pieza: { tipo: "recta", anclaje: "B" }, robot: {}, fuente: {} };
let evaluacion = null;   // último estado del evaluador en vivo
let tipoPintado = null;
let hablado = -1;
let imagenRobot = false;  // ya llegó alguna imagen de la cámara del robot simulado

// --- escena 3D ---------------------------------------------------------------------------------------------
const lienzo = $("lienzo");
const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
const escena = new THREE.Scene();
const camara = new THREE.PerspectiveCamera(30, 1, 1, 5000);
camara.up.set(0, 0, 1);

escena.add(new THREE.HemisphereLight(0xc9dcff, 0x1b140e, 1.1));
const sol = new THREE.DirectionalLight(0xffffff, 2.0);
sol.position.set(-60, -140, 240);
escena.add(sol);
const contraluz = new THREE.DirectionalLight(0x8fb7ff, 0.7);
contraluz.position.set(160, 160, 120);
escena.add(contraluz);

const rejilla = new THREE.GridHelper(600, 60, 0x283244, 0x18202b);
rejilla.rotation.x = Math.PI / 2;
rejilla.position.set(60, 0, -6.2);
escena.add(rejilla);

const grupoPieza = new THREE.Group();
escena.add(grupoPieza);
const grupoMarcas = new THREE.Group();  // huecos marcados sobre la pieza
escena.add(grupoMarcas);

function texturaResplandor(color) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, "rgba(255,255,255,1)");
  gr.addColorStop(0.18, color);
  gr.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = gr;
  g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function texturaAruco() {
  // Marcador estilizado (6x6 celdas con borde negro y margen blanco): solo para reconocer la pieza en el gemelo.
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d");
  g.fillStyle = "#f4f4f4";
  g.fillRect(0, 0, 256, 256);
  const m = 256 * 5 / 35, celda = (256 - 2 * m) / 6;
  g.fillStyle = "#111";
  g.fillRect(m, m, 256 - 2 * m, 256 - 2 * m);
  const bits = [0b0110, 0b1011, 0b0101, 0b1100];
  g.fillStyle = "#f4f4f4";
  for (let f = 0; f < 4; f++) for (let k = 0; k < 4; k++)
    if ((bits[f] >> k) & 1) g.fillRect(m + celda * (k + 1), m + celda * (f + 1), celda, celda);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const matAcero = new THREE.MeshStandardMaterial({ color: 0x8b929c, metalness: 0.55, roughness: 0.4 });
const matBorde = new THREE.LineBasicMaterial({ color: 0x3b4352 });

function caja(x0, x1, y0, y1, z0, z1, mat = matAcero) {
  const g = new THREE.BoxGeometry(x1 - x0, y1 - y0, z1 - z0);
  const m = new THREE.Mesh(g, mat);
  m.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
  const bordes = new THREE.LineSegments(new THREE.EdgesGeometry(g), matBorde);
  m.add(bordes);
  return m;
}

function construirPieza(tipo) {
  grupoPieza.clear();
  if (!C) return;
  const L = C.longitud_cordon, mx = C.margen_x, a = C.chapa.ancho, e = C.chapa.grosor, g = C.holgura_junta / 2;
  const x0 = -mx, x1 = L + mx;
  if (tipo === "t") {
    grupoPieza.add(caja(x0, x1, -a, a, -e, 0));
    grupoPieza.add(caja(x0, x1, 0, C.alma.grosor, 0, C.alma.alto));
  } else {
    grupoPieza.add(caja(x0, x1, g, g + a, -e, 0));
    grupoPieza.add(caja(x0, x1, -g - a, -g, -e, 0));
    // fondo oscuro de la junta
    grupoPieza.add(caja(x0, x1, -g, g, -e, -e + 0.6, new THREE.MeshStandardMaterial({ color: 0x15181d })));
  }
  // ArUco de la pieza
  const [cx, cy] = C.aruco_pieza.centro;
  const lado = C.aruco_pieza.lado + 2 * C.aruco_pieza.margen;
  const aruco = new THREE.Mesh(new THREE.PlaneGeometry(lado, lado),
    new THREE.MeshStandardMaterial({ map: texturaAruco(), roughness: 0.8 }));
  aruco.position.set(cx, cy, 0.05);
  grupoPieza.add(aruco);
  // Marcas del cordón: una cada tramo, más larga cada 30 mm, delante de la junta.
  const pts = [];
  const yMarca = tipo === "t" ? -6 : -g - 1.2;
  for (let i = 0; i <= C.n_tramos; i++) {
    const x = i * C.tamano_tramo, largo = i % 6 === 0 ? 3.5 : 1.6;
    pts.push(new THREE.Vector3(x, yMarca, 0.08), new THREE.Vector3(x, yMarca - largo, 0.08));
  }
  const marcas = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color: 0x2d3340 }));
  grupoPieza.add(marcas);
  encuadrar(tipo);
}

function encuadrar(tipo) {
  const t = tipo === "t";
  const objetivo = new THREE.Vector3(t ? 62 : 60, t ? 4 : -4, t ? 8 : -3);
  const ancho = lienzo.clientWidth || 800, alto = lienzo.clientHeight || 500;
  const aspecto = ancho / alto;
  // Distancia para que la pieza (140 x 82 mm) llene el gemelo sin tapar la orden del robot ni el consejo.
  const dist = (aspecto < 1.45 ? 300 : 262) * (t ? 1.14 : 1.0);
  const dir = (t ? new THREE.Vector3(-0.42, -0.6, 0.62) : new THREE.Vector3(-0.15, -0.68, 0.72)).normalize();
  camara.position.copy(objetivo).addScaledVector(dir, dist);
  camara.lookAt(objetivo);
}

// Cordones: esferas aplastadas (InstancedMesh), una cada ~0,8 mm, coloreadas por calidad.
const geoGota = new THREE.SphereGeometry(1, 14, 10);
function crearCordon(max, emisivo) {
  const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.25, roughness: 0.35,
    emissive: emisivo, emissiveIntensity: 0.35 });
  const malla = new THREE.InstancedMesh(geoGota, mat, max);
  malla.count = 0;
  malla.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  malla.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
  malla.frustumCulled = false;
  escena.add(malla);
  return { malla, max, previa: null };
}
const cordonAlumno = crearCordon(9000, 0x000000);
const cordonRobot = crearCordon(6000, 0x0a3550);
const _m = new THREE.Matrix4(), _c = new THREE.Color(), _q = new THREE.Quaternion();

function ponerGota(cordon, x, y, color) {
  const { malla } = cordon;
  if (malla.count >= cordon.max) return;
  const t = tipoPintado === "t";
  const escala = t ? new THREE.Vector3(2.3, 2.3, 2.3) : new THREE.Vector3(2.5, 2.5, 1.05);
  const pos = new THREE.Vector3(x, y + (t ? -1.1 : 0), t ? 1.1 : 0.35);
  _m.compose(pos, _q, escala);
  malla.setMatrixAt(malla.count, _m);
  malla.setColorAt(malla.count, _c.setHex(color));
  malla.count++;
  malla.instanceMatrix.needsUpdate = true;
  malla.instanceColor.needsUpdate = true;
}

function anadirAlCordon(cordon, x, y, activo, color) {
  const p = cordon.previa;
  if (activo) {
    if (p && p.activo) {
      const d = Math.hypot(x - p.x, y - p.y);
      if (d < 8) {
        const n = Math.max(1, Math.ceil(d / 0.8));
        for (let k = 1; k <= n; k++) ponerGota(cordon, p.x + (x - p.x) * k / n, p.y + (y - p.y) * k / n, color);
      } else ponerGota(cordon, x, y, color);
    } else ponerGota(cordon, x, y, color);
  }
  cordon.previa = { x, y, activo };
}

function vaciarCordon(cordon) {
  cordon.malla.count = 0;
  cordon.previa = null;
}

// Antorchas: boquilla + cuerpo orientados con los ángulos; LED/arco como sprite brillante.
function crearAntorcha(colorCuerpo, colorLuz, colorPunto) {
  const g = new THREE.Group();
  const cuerpo = new THREE.Group();
  const boquilla = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 4.2, 16, 20),
    new THREE.MeshStandardMaterial({ color: 0xc58a4a, metalness: 0.8, roughness: 0.3 }));
  boquilla.position.y = 3 + 8;
  const mango = new THREE.Mesh(new THREE.CylinderGeometry(5.2, 5.2, 60, 20),
    new THREE.MeshStandardMaterial({ color: colorCuerpo, metalness: 0.2, roughness: 0.55 }));
  mango.position.y = 3 + 16 + 30;
  cuerpo.add(boquilla, mango);
  g.add(cuerpo);
  const brillo = new THREE.Sprite(new THREE.SpriteMaterial({ map: texturaResplandor(colorLuz), color: 0xffffff,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  brillo.scale.set(16, 16, 1);
  g.add(brillo);
  const luz = new THREE.PointLight(colorPunto, 0, 90, 1.6);
  luz.position.z = 4;
  g.add(luz);
  g.visible = false;
  escena.add(g);
  return { g, cuerpo, brillo, luz, visto: 0 };
}
const antorchaAlumno = crearAntorcha(0x4a5363, "rgba(140,255,120,0.9)", 0x8cff78);
const antorchaRobot = crearAntorcha(0xd9572b, "rgba(150,215,255,0.95)", 0x96d7ff);

function orientar(antorcha, trabajo, avance) {
  // Eje mango → punta en el marco de la pieza (mismo convenio que lewelder/antorcha.py).
  const t = THREE.MathUtils.degToRad(Math.min(179, Math.max(1, trabajo ?? 90)));
  const v = THREE.MathUtils.degToRad(Math.min(89, Math.max(-89, avance ?? 0)));
  const eje = new THREE.Vector3(Math.tan(v), 1 / Math.tan(t), -1).normalize();
  // El cuerpo del modelo va a lo largo de +Y local desde la punta: +Y local = -eje.
  antorcha.cuerpo.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), eje.clone().negate());
}

function ponerPunta(antorcha, x, y, z) {
  antorcha.g.position.set(x, y, z);
  antorcha.g.visible = true;
  antorcha.visto = performance.now();
}

// Marcas de los huecos sobre la pieza: rojo pendiente, cian repasado.
function pintarMarcasHuecos() {
  grupoMarcas.clear();
  const huecos = (E.modo === "repaso" ? E.huecos_robot : E.huecos) || [];
  if (!["nota", "repaso"].includes(E.modo) || !C) return;
  const t = tipoPintado === "t";
  const rep = E.repasados || [];
  for (const [a, b] of huecos) {
    for (let x = a; x < b; x += C.tamano_tramo) {
      const i = Math.round(x / C.tamano_tramo);
      const hecho = rep[i];
      const mat = new THREE.MeshBasicMaterial({ color: hecho ? 0x38bdf8 : 0xff4d4f, transparent: true,
        opacity: hecho ? 0.22 : 0.6, depthWrite: false });
      const m = new THREE.Mesh(new THREE.BoxGeometry(C.tamano_tramo - 0.6, 9, 0.5), mat);
      m.position.set(x + C.tamano_tramo / 2, t ? -4.5 : 0, 0.3);
      grupoMarcas.add(m);
    }
  }
}

function redimensionar() {
  const w = lienzo.clientWidth, h = lienzo.clientHeight;
  if (!w || !h) return;
  if (lienzo.width !== Math.round(w * renderer.getPixelRatio()) || lienzo.height !== Math.round(h * renderer.getPixelRatio())) {
    renderer.setSize(w, h, false);
    camara.aspect = w / h;
    camara.updateProjectionMatrix();
    encuadrar(tipoPintado);
  }
}

function animar(ahora) {
  redimensionar();
  const parpadeo = 0.85 + 0.15 * Math.sin(ahora / 37) * Math.sin(ahora / 13);
  // Antorcha del alumno: se esconde si la cámara deja de ver el LED.
  if (antorchaAlumno.g.visible && ahora - antorchaAlumno.visto > 700) antorchaAlumno.g.visible = false;
  const ledRobot = !!E.robot?.led;
  antorchaRobot.brillo.visible = true;
  antorchaRobot.brillo.scale.setScalar(ledRobot ? 26 * parpadeo : 5);
  antorchaRobot.brillo.material.opacity = ledRobot ? 1 : 0.35;
  antorchaRobot.luz.intensity = ledRobot ? 9000 * parpadeo : 0;
  antorchaAlumno.luz.intensity = antorchaAlumno.encendido ? 4500 * parpadeo : 0;
  antorchaAlumno.brillo.scale.setScalar(antorchaAlumno.encendido ? 18 * parpadeo : 6);
  renderer.render(escena, camara);
  requestAnimationFrame(animar);
}

// --- interfaz ----------------------------------------------------------------------------------------------
const celdas = [];
for (let i = 0; i < 24; i++) {
  const d = document.createElement("div");
  d.className = "tramo";
  $("tramos").appendChild(d);
  celdas.push(d);
}

function f1(v) { return v == null ? "–" : v.toFixed(1).replace(".", ","); }
function tol() { return C ? C.tolerancias[E.nivel] : 5; }

function metrica(id, palabra, valor, clase) {
  const el = $(id);
  el.className = "metrica " + (clase || "");
  el.querySelector(".m-palabra").textContent = palabra;
  el.querySelector(".m-valor").textContent = valor;
}

function pintarMetricasResultado(r) {
  const t = r.tolerancia_mm;
  const cob = r.cobertura_pct;
  metrica("m-cobertura", cob >= 100 ? "completo" : cob >= 85 ? "casi completo" : "con huecos",
    `${Math.round(cob)} %`, cob >= 100 ? "bien" : cob >= 85 ? "regular" : "mal");
  const v = r.velocidad_media, cv = r.cv_velocidad;
  let ritmo = ["constante", "bien"];
  if (r.duracion_s === 0) ritmo = ["sin soldar", "mal"];
  else if (v > 6) ritmo = ["rápido", "regular"];
  else if (v < 4) ritmo = ["lento", "regular"];
  else if (cv > 0.25) ritmo = ["a tirones", "regular"];
  metrica("m-regularidad", ritmo[0], `${f1(v)} mm/s`, ritmo[1]);
  const n = r.n_quemados;
  metrica("m-quemados", n === 0 ? "ninguno" : n === 1 ? "1 punto" : `${n} puntos`,
    n ? r.puntos_quemados.map((x) => `${Math.round(x)} mm`).join(" · ") : "–", n ? "mal" : "bien");
  const d = r.desvio_medio_mm;
  metrica("m-desvio", d < t / 3 ? "centrado" : d < t / 2 ? "algo desviado" : "fuera de cordón",
    `${f1(d)} mm`, d < t / 3 ? "bien" : d < t / 2 ? "regular" : "mal");
  const pa = r.pct_tiempo_angulo_ok;
  if (pa == null) metrica("m-angulo", "sin IMU", "–", "");
  else metrica("m-angulo", pa >= 80 ? "firme" : pa >= 50 ? "inestable" : "mal ángulo",
    `${Math.round(r.angulo_trabajo_medio ?? 0)}° · ${Math.round(r.angulo_avance_medio ?? 0)}°`,
    pa >= 80 ? "bien" : pa >= 50 ? "regular" : "mal");
}

function pintarMetricasVivo(ev) {
  if (!ev) {
    for (const id of ["m-cobertura", "m-regularidad", "m-quemados", "m-desvio", "m-angulo"]) metrica(id, "–", "–", "");
    return;
  }
  metrica("m-cobertura", "soldando…", `${Math.round(ev.cobertura_pct || 0)} %`, "");
  const v = ev.velocidad ?? 0, [v0, v1] = C ? C.velocidad_objetivo : [4, 6];
  if (!ev.gatillo) metrica("m-regularidad", "–", `${f1(v)} mm/s`, "");
  else metrica("m-regularidad", v > v1 ? "rápido" : v < v0 ? "lento" : "buen ritmo", `${f1(v)} mm/s`,
    v > v1 || v < v0 ? "regular" : "bien");
  const n = (ev.puntos_quemados || []).length;
  metrica("m-quemados", n === 0 ? "ninguno" : `${n} punto${n > 1 ? "s" : ""}`, "–", n ? "mal" : "bien");
  const y = ev.posicion ? Math.abs(ev.posicion.y) : null;
  if (y == null) metrica("m-desvio", "–", "–", "");
  else metrica("m-desvio", y < tol() / 3 ? "centrado" : y < tol() ? "algo desviado" : "fuera de cordón",
    `${f1(y)} mm`, y < tol() / 3 ? "bien" : y < tol() ? "regular" : "mal");
  const tr = ev.angulo_trabajo, av = ev.angulo_avance;
  if (tr == null) metrica("m-angulo", "sin IMU", "–", "");
  else {
    const obj = C ? C.angulo_trabajo_objetivo[E.pieza?.tipo || "recta"] : 90;
    const ok = Math.abs(tr - obj) <= (C ? C.margen_angulo_trabajo : 15) && av >= 0 && av <= 20;
    metrica("m-angulo", ok ? "firme" : "corrige", `${Math.round(tr)}° · ${Math.round(av)}°`, ok ? "bien" : "regular");
  }
}

function claseTramo(tr, t) {
  if (tr.quemado) return "quemado";
  const v = tr.velocidad_media;
  if ((tr.desvio_medio_mm ?? 0) > t / 2 || (v != null && (v < 4 || v > 6)) || tr.angulo_correcto === false) return "regular";
  return "bien";
}

function pintarTramos() {
  const r = E.resultado;
  const rep = E.repasados || [];
  const quemadosVivo = new Set((evaluacion?.puntos_quemados || []).map((x) => Math.min(23, Math.floor(x / 5))));
  for (let i = 0; i < 24; i++) {
    let cls = "tramo";
    if (E.modo === "maestro") cls += rep[i] ? " robot" : "";
    else if (r && ["nota", "repaso", "certificado"].includes(E.modo)) {
      const tr = r.tramos[i];
      if (!tr.cubierto) cls += rep[i] ? " robot" : " hueco";
      else cls += " " + claseTramo(tr, r.tolerancia_mm);
    } else if (E.modo === "examen" && evaluacion) {
      if (quemadosVivo.has(i)) cls += " quemado";
      else if (evaluacion.tramos_cubiertos?.[i]) cls += " bien";
    }
    if (i === tramoPunta) cls += " punta";
    celdas[i].className = cls;
  }
}
let tramoPunta = -1;

function pintarNota() {
  const tarjeta = $("nota-tarjeta"), ver = $("veredicto");
  const r = E.resultado;
  const t = C ? C.tolerancias[E.nivel] : 5, ap = C ? C.nota_aprobado[E.nivel] : 6;
  $("nota-pie").textContent = `Nivel ${E.nivel} · tolerancia ±${t} mm · aprueba con ${String(ap).replace(".", ",")}`;
  if (r && E.modo !== "examen" && E.modo !== "espera" && !(E.modo === "maestro" && !E.resultado)) {
    $("nota").textContent = f1(r.nota);
    $("nota-etiqueta").textContent = "Nota del examen";
    tarjeta.className = "tarjeta nota-tarjeta " + (r.aprobado ? "aprobado" : "suspenso");
    ver.className = "veredicto " + (r.aprobado ? "aprobado" : "suspenso");
    ver.textContent = r.aprobado ? "APROBADO" : "SUSPENSO";
    pintarMetricasResultado(r);
  } else if (E.modo === "examen") {
    const np = evaluacion?.nota_parcial;
    $("nota").textContent = np == null ? "–" : f1(np);
    $("nota-etiqueta").textContent = "Nota provisional";
    tarjeta.className = "tarjeta nota-tarjeta provisional";
    ver.className = "veredicto provisional";
    ver.textContent = "EN CURSO";
    pintarMetricasVivo(evaluacion);
  } else {
    $("nota").textContent = "–";
    $("nota-etiqueta").textContent = "Nota";
    tarjeta.className = "tarjeta nota-tarjeta";
    ver.className = "veredicto";
    ver.textContent = "";
    pintarMetricasVivo(null);
  }
}

function consejo() {
  const raton = E.fuente?.fuente === "raton";
  const huecos = (E.huecos || []).length;
  switch (E.modo) {
    case "espera":
      return raton ? "Pulsa Empezar examen y suelda arrastrando el dedo sobre la junta."
        : "Antorcha vertical y pulsa Tara. Después, Empezar examen.";
    case "examen":
      return raton ? "Mantén pulsado y arrastra sobre la junta, de izquierda a derecha."
        : "Suelda de izquierda a derecha, a ritmo constante.";
    case "nota":
      if (E.certificable) return "Sin huecos: ¡certificado! Pulsa Ver certificado.";
      return huecos ? (huecos > 1 ? `Has dejado ${huecos} huecos: pulsa Repaso y el robot los suelda.`
        : "Has dejado un hueco: pulsa Repaso y el robot lo suelda.")
        : "Sin huecos, pero hay que mejorar. Prueba otra vez o mira cómo suelda el robot.";
    case "repaso":
      return E.robot?.terminado ? `Pieza terminada: cordón completo al ${Math.round(E.cobertura_final ?? 100)} %.`
        : "El robot recorre todo el cordón: el LED solo se enciende en los huecos.";
    case "maestro":
      return E.robot?.terminado ? "El robot ha terminado el cordón." : "El robot suelda el cordón entero.";
    default:
      return "";
  }
}

function pintarEstado() {
  document.body.dataset.modo = E.modo;
  $("modo").textContent = NOMBRE_MODO[E.modo] || E.modo;
  const tipo = E.pieza?.tipo || "recta";
  $("pieza-texto").textContent = `Unión ${tipo === "t" ? "en T" : "recta"} · anclaje ${E.pieza?.anclaje ?? "?"}`;
  if (C && tipo !== tipoPintado) {
    tipoPintado = tipo;
    construirPieza(tipo);
  }
  const f = E.fuente || {};
  const sim = f.fuente === "simulada", raton = f.fuente === "raton";
  $("ajustes-sim").hidden = !(sim || raton);
  $("lbl-pasada").hidden = !sim;
  $("sel-tipo").value = tipo;
  $("sel-anclaje").value = E.pieza?.anclaje || "B";
  const selPasada = $("sel-pasada");
  if (selPasada.options.length !== (E.pasadas_preparadas || []).length) {
    selPasada.innerHTML = "";
    for (const p of E.pasadas_preparadas || []) {
      const o = document.createElement("option");
      o.value = p;
      o.textContent = p.replace("_", " ");
      selPasada.appendChild(o);
    }
  }
  const bloqueadoPieza = !["espera", "nota", "certificado"].includes(E.modo) || E.robot?.ocupado;
  for (const id of ["sel-tipo", "sel-anclaje", "sel-pasada"]) $(id).disabled = bloqueadoPieza;
  marcar("ind-fuente", raton || f.camara);
  $("ind-antorcha").hidden = raton;
  $("ind-tara").hidden = raton;
  marcar("ind-antorcha", f.antorcha);
  marcar("ind-tara", f.tara);

  const examen = E.modo === "examen", ocupado = !!E.robot?.ocupado;
  $("b-tara").disabled = raton || examen;
  $("b-examen").hidden = examen;
  $("b-examen").disabled = ocupado;
  $("b-examen").textContent = E.modo === "espera" ? "Empezar examen" : "Nuevo examen";
  $("b-terminar").hidden = !examen;
  $("b-repaso").disabled = !E.puede_repaso;
  $("b-certificado").hidden = !(E.modo === "nota" && E.certificable);
  $("b-certificado").className = "boton dorado";
  $("b-maestro").disabled = examen || ocupado;
  for (const b of $("niveles").querySelectorAll("button")) {
    b.classList.toggle("activo", b.dataset.nivel === E.nivel);
    b.disabled = examen || ocupado;
  }

  const conRobot = ["repaso", "maestro"].includes(E.modo);
  $("panel-robot").hidden = !conRobot;
  $("robot-vista").hidden = !(conRobot && imagenRobot);
  if (conRobot) pintarRobot();
  if (!conRobot) antorchaRobot.g.visible = false;

  pintarNota();
  pintarTramos();
  pintarMarcasHuecos();
  pintarValoracion();
  $("consejo").textContent = consejo();
  $("consejo").hidden = !consejo();

  const cert = E.modo === "certificado" && E.certificado;
  $("certificado").hidden = !cert;
  if (cert) {
    const k = E.certificado;
    $("cert-titulo").textContent = k.titulo;
    $("cert-texto").textContent = `Se certifica que el alumno ha soldado una unión ${k.union} completa, sin huecos, ` +
      `con la tolerancia de nivel ${k.nivel} (±${C ? C.tolerancias[k.nivel] : 5} mm), evaluado por el sistema LeWelder.`;
    $("cert-nota").textContent = f1(k.nota);
    $("cert-nivel").textContent = NOMBRE_NIVEL[k.nivel] || k.nivel;
    $("cert-fecha").textContent = k.fecha;
  }
}

function pintarRobot() {
  const r = E.robot || {};
  $("instruccion").textContent = `«${E.instruccion || ""}»`;
  for (const b of $("politicas").querySelectorAll("button")) b.classList.toggle("activo", b.dataset.politica === r.politica);
  // Respaldo: la política elegida no está y el robot usa otra (vla → act → replay).
  const respaldo = r.politica_activa && r.politica_activa !== r.politica ? r.politica_activa : null;
  for (const b of $("politicas").querySelectorAll("button")) b.classList.toggle("respaldo", b.dataset.politica === respaldo);
  $("respaldo-politica").hidden = !respaldo;
  if (respaldo) {
    $("respaldo-politica").textContent = `Respaldo: usa ${NOMBRE_POLITICA[respaldo] || respaldo}`;
    $("respaldo-politica").title = r.aviso_politica || "";
  }
  const led = !!r.led;
  $("led-robot").classList.toggle("encendido", led);
  $("led-texto").textContent = led ? (E.modo === "repaso" ? "LED encendido · soldando hueco" : "LED encendido · soldando")
    : r.terminado ? "Terminado" : "LED apagado";
  $("progreso-robot").style.width = `${Math.round(100 * (r.progreso || 0))}%`;
}

function pintarValoracion() {
  const v = E.valoracion;
  const ver = v && ["nota", "repaso", "certificado"].includes(E.modo);
  $("maestro-dice").hidden = !ver;
  if (!ver) return;
  $("valoracion").textContent = v.texto;
  $("origen-valoracion").textContent = v.origen === "llm" ? "· IA" : "· reglas";
}

function marcar(id, ok) {
  const el = $(id);
  el.classList.toggle("ok", !!ok);
  el.classList.toggle("mal", !ok);
}

function mostrarAviso(texto, prioridad = "media", duracion = 4500) {
  const caja = $("avisos");
  const frase = texto.charAt(0).toUpperCase() + texto.slice(1);
  // Si el mismo aviso sigue en pantalla, se refresca (sube y vuelve a contar) en vez de apilarse.
  for (const viejo of [...caja.children]) if (viejo.textContent === frase) viejo.remove();
  const d = document.createElement("div");
  d.className = `aviso ${prioridad}`;
  d.textContent = frase;
  caja.prepend(d);
  while (caja.children.length > 4) caja.lastChild.remove();
  setTimeout(() => d.classList.add("sale"), duracion);
  setTimeout(() => d.remove(), duracion + 600);
}

function hablar(texto) {
  if (!("speechSynthesis" in window) || !texto) return;
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = "es-ES";
    const voces = speechSynthesis.getVoices();
    const voz = voces.find((v) => v.lang === "es-ES") || voces.find((v) => v.lang?.startsWith("es"));
    if (voz) u.voice = voz;
    u.rate = 1.0;
    u.pitch = 0.92;
    speechSynthesis.speak(u);
  } catch (e) { /* sin voz: el texto ya está en pantalla */ }
}

// --- mensajes del servidor ---------------------------------------------------------------------------------
function alMensaje(msg) {
  switch (msg.tipo) {
    case "estado": {
      const anterior = E.modo;
      const robotAntes = E.robot?.ocupado;
      E = msg;
      if (msg.modo === "examen" && anterior !== "examen") {
        vaciarCordon(cordonAlumno);
        vaciarCordon(cordonRobot);
        evaluacion = null;
        $("avisos").innerHTML = "";
        hablado = -1;
      }
      if (["repaso", "maestro"].includes(msg.modo) && msg.robot?.ocupado && !robotAntes) vaciarCordon(cordonRobot);
      if (msg.modo === "espera" && anterior !== "espera") {
        vaciarCordon(cordonAlumno);
        vaciarCordon(cordonRobot);
        evaluacion = null;
      }
      if (msg.modo === "maestro" && anterior !== "maestro") vaciarCordon(cordonAlumno);
      if (msg.modo === "examen" || msg.modo === "espera") tramoPunta = -1;
      pintarEstado();
      break;
    }
    case "historial":
      vaciarCordon(cordonAlumno);
      vaciarCordon(cordonRobot);
      for (const m of msg.alumno || []) anadirAlCordon(cordonAlumno, m.x, m.y, m.gatillo && m.z <= 15, COLORES[m.calidad] || COLORES.bien);
      for (const m of msg.robot || []) anadirAlCordon(cordonRobot, m.x, m.y, m.led, COLORES.robot);
      break;
    case "muestra": {
      const soldando = msg.gatillo && msg.z <= (C ? C.z_levantada : 15);
      antorchaAlumno.encendido = !!msg.gatillo;
      if (msg.gatillo) ponerPunta(antorchaAlumno, msg.x, msg.y, msg.z);
      orientar(antorchaAlumno, msg.angulo_trabajo ?? (E.pieza?.tipo === "t" ? 45 : 90), msg.angulo_avance ?? 10);
      if (E.modo === "examen") {
        anadirAlCordon(cordonAlumno, msg.x, msg.y, soldando, COLORES[msg.calidad] || COLORES.bien);
        tramoPunta = msg.gatillo && msg.x >= 0 && msg.x < 120 ? Math.floor(msg.x / 5) : -1;
      }
      break;
    }
    case "evaluacion":
      evaluacion = msg;
      if (E.modo === "examen") {
        pintarNota();
        pintarTramos();
      }
      break;
    case "aviso":
      mostrarAviso(msg.texto, msg.prioridad);
      break;
    case "resultado":
      E.resultado = msg.resultado;
      tramoPunta = -1;
      pintarEstado();
      break;
    case "valoracion":
      E.valoracion = msg;
      pintarValoracion();
      if (msg.id_pasada !== hablado) {
        hablado = msg.id_pasada;
        hablar(msg.texto);
      }
      break;
    case "robot": {
      E.robot = { ...(E.robot || {}), led: msg.led, politica: msg.politica, progreso: msg.progreso,
        politica_activa: msg.politica_activa, aviso_politica: msg.aviso_politica };
      E.repasados = msg.repasados;
      if (msg.punta) {
        ponerPunta(antorchaRobot, msg.punta.x, msg.punta.y, msg.punta.z);
        // El brazo en reposo deja la punta lejos de la pieza (robot MuJoCo): fuera del gemelo no se dibuja.
        antorchaRobot.g.visible = Math.abs(msg.punta.y) < 70 && msg.punta.x > -40 && msg.punta.x < 160 && msg.punta.z < 120;
        orientar(antorchaRobot, E.pieza?.tipo === "t" ? 45 : 90, 10);
        anadirAlCordon(cordonRobot, msg.punta.x, msg.punta.y, msg.led, COLORES.robot);
        tramoPunta = msg.punta.x >= 0 && msg.punta.x < 120 && msg.punta.z < 15 && Math.abs(msg.punta.y) < 20
          ? Math.floor(msg.punta.x / 5) : -1;
      }
      pintarRobot();
      pintarTramos();
      if (E.modo === "repaso") pintarMarcasHuecos();
      break;
    }
    case "robot_imagen":
      // Fotograma de la cámara cenital del robot simulado (solo con --robot mujoco).
      if (["repaso", "maestro"].includes(E.modo)) {
        $("robot-imagen").src = `data:image/jpeg;base64,${msg.jpeg}`;
        if (!imagenRobot) { imagenRobot = true; $("robot-vista").hidden = false; }
      }
      break;
    case "robot_fin":
      E.repasados = msg.repasados;
      tramoPunta = -1;
      if (msg.modo === "repaso") mostrarAviso(`Repaso terminado: cordón al ${Math.round(msg.cobertura_final ?? 100)} %`, "info", 6000);
      else mostrarAviso("El robot ha terminado el cordón", "info", 5000);
      break;
    case "info":
      mostrarAviso(msg.texto, "info", 3000);
      break;
    case "error":
      mostrarAviso(msg.texto, "alta", 4000);
      break;
  }
}

// --- conexión ----------------------------------------------------------------------------------------------
let ws = null;
function conectar() {
  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
  ws = new WebSocket(url);
  ws.onopen = () => { $("sin-conexion").hidden = true; marcar("ind-servidor", true); };
  ws.onmessage = (e) => { try { alMensaje(JSON.parse(e.data)); } catch (err) { console.error(err); } };
  ws.onclose = () => {
    $("sin-conexion").hidden = false;
    marcar("ind-servidor", false);
    setTimeout(conectar, 1000);
  };
}
function enviar(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

// --- botones -----------------------------------------------------------------------------------------------
$("b-tara").onclick = () => enviar({ orden: "tara" });
$("b-examen").onclick = () => { if ("speechSynthesis" in window) speechSynthesis.cancel(); enviar({ orden: "empezar_examen" }); };
$("b-terminar").onclick = () => enviar({ orden: "terminar" });
$("b-repaso").onclick = () => enviar({ orden: "repaso" });
$("b-certificado").onclick = () => enviar({ orden: "certificado" });
$("b-maestro").onclick = () => enviar({ orden: "maestro" });
$("b-reiniciar").onclick = () => { if ("speechSynthesis" in window) speechSynthesis.cancel(); enviar({ orden: "reiniciar" }); };
$("cert-maestro").onclick = () => enviar({ orden: "maestro", tipo: "t" });
$("cert-cerrar").onclick = () => enviar({ orden: "reiniciar" });
$("escuchar").onclick = () => hablar(E.valoracion?.texto);
for (const b of $("niveles").querySelectorAll("button")) b.onclick = () => enviar({ orden: "nivel", nivel: b.dataset.nivel });
for (const b of $("politicas").querySelectorAll("button")) b.onclick = () => enviar({ orden: "politica", politica: b.dataset.politica });
$("sel-tipo").onchange = (e) => enviar({ orden: "pieza", tipo: e.target.value });
$("sel-anclaje").onchange = (e) => enviar({ orden: "pieza", anclaje: e.target.value });
$("sel-pasada").onchange = (e) => enviar({ orden: "simulacion", pasada: e.target.value });

// Fuente ratón: el dedo sobre el gemelo es la punta; mantener pulsado es el gatillo.
const rayo = new THREE.Raycaster(), plano = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0), _p = new THREE.Vector3();
let pulsado = false, ultimoEnvio = 0;
function puntoEnPieza(ev) {
  const r = lienzo.getBoundingClientRect();
  rayo.setFromCamera(new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1), camara);
  return rayo.ray.intersectPlane(plano, _p);
}
function enviarRaton(ev, gatillo, forzar = false) {
  if (E.fuente?.fuente !== "raton") return;
  const ahora = performance.now();
  if (!forzar && ahora - ultimoEnvio < 16) return;
  const p = puntoEnPieza(ev);
  if (!p) return;
  ultimoEnvio = ahora;
  enviar({ orden: "raton", x: +p.x.toFixed(2), y: +p.y.toFixed(2), gatillo });
}
lienzo.addEventListener("pointerdown", (ev) => { pulsado = true; lienzo.setPointerCapture(ev.pointerId); enviarRaton(ev, true, true); });
lienzo.addEventListener("pointermove", (ev) => { if (pulsado) enviarRaton(ev, true); });
for (const tipo of ["pointerup", "pointercancel"]) lienzo.addEventListener(tipo, (ev) => { if (pulsado) enviarRaton(ev, false, true); pulsado = false; });

// --- arranque ----------------------------------------------------------------------------------------------
fetch("api/contrato").then((r) => r.json()).then((contrato) => {
  C = contrato;
  tipoPintado = E.pieza?.tipo || "recta";
  construirPieza(tipoPintado);
  pintarEstado();
}).catch(() => mostrarAviso("No se pudo leer el contrato del servidor", "alta"));
if ("speechSynthesis" in window) speechSynthesis.getVoices();
conectar();
requestAnimationFrame(animar);
// Para depurar y para las pruebas con Playwright: estado, enviar órdenes y proyectar un punto de la pieza a píxeles.
window.lewelder = {
  get estado() { return E; },
  enviar,
  proyectar(x, y, z = 0) {
    const v = new THREE.Vector3(x, y, z).project(camara), r = lienzo.getBoundingClientRect();
    return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height };
  },
};
