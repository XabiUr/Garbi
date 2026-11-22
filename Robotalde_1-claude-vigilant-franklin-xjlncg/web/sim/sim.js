// LeWelder · simulador: la mesa en 3D (SO-101, piezas del CAD, webcams) y el panel del juez.
// Habla con el servidor por `/ws_sim` (lewelder/simulador.py): recibe `escena`, `mundo` a 30 Hz y todo lo que va a
// la tablet (`PROTOCOLO.md`); manda la antorcha del juez, las órdenes y las perturbaciones.
// Marco: el de la mesa del contrato (mm, Z arriba). three.js trabaja directamente en él (camera.up = Z).
import * as THREE from "three";

const params = new URLSearchParams(location.search);
// Partida de esta pestaña: la de la URL o una nueva (el servidor en modo "una" las junta todas en la principal).
let PARTIDA = params.get("partida");
if (!PARTIDA) {
  try { PARTIDA = sessionStorage.getItem("lewelder.partida"); } catch (e) { /* sin almacenamiento */ }
  PARTIDA = PARTIDA || Math.random().toString(36).slice(2, 10);
  params.set("partida", PARTIDA);
  history.replaceState(null, "", `${location.pathname}?${params}`);
}
try { sessionStorage.setItem("lewelder.partida", PARTIDA); } catch (e) { /* sin almacenamiento */ }
const conPartida = (ruta) => `${ruta}${ruta.includes("?") ? "&" : "?"}partida=${encodeURIComponent(PARTIDA)}`;
const iframe = document.getElementById("tablet");
if (iframe) iframe.src = conPartida("/v2/index.html");
const raiz = document.getElementById("raiz");
const VISTA = raiz.dataset.vista;
const $ = (s, el = document) => el.querySelector(s);

// --- colores del plano ------------------------------------------------------------------------------------------
const COL = {
  trazo: 0xeef6ff, trazo2: 0xb8d5f3, trazo3: 0x7fa6cf, cian: 0x74d6ff, arco: 0xff8a1f, arcoClaro: 0xffc56b,
  rojo: 0xff5148, verde: 0x6dffb0, relleno: 0x1a5591, rellenoClaro: 0x2a6fb5,
};
const CALIDAD = { bien: 0xffc56b, regular: 0xff8a1f, quemado: 0xff5148, suelto: 0x7fa6cf };

// --- DOM: capas sobre la mesa y panel ------------------------------------------------------------------------
const mesaEl = $("#mesa");
mesaEl.innerHTML = `
  <canvas id="lienzo"></canvas>
  <div class="etiquetas" id="etiquetas"></div>
  <div class="cabecera-mesa"><h1>LEWELDER · MESA</h1><div class="sub">SIMULADOR DE LA DEMO · SO-101 EN MUJOCO · CAD v2</div></div>
  <div class="pantalla-actual" id="pantalla">PANTALLA · —</div>
  <div class="partida" id="partida"></div>
  <div class="robot-estado" id="robot-estado"><div id="robot-texto">CHISPAS · EN REPOSO</div><div class="barra"><i id="robot-barra"></i></div></div>
  <div class="bocadillo" id="bocadillo" style="opacity:0"><b>CHISPAS</b><span id="bocadillo-texto"></span></div>
  <div class="hud"><div class="puntos" id="hud-puntos">0</div><div class="combo" id="hud-combo">COMBO ×1</div></div>
  <div class="sello" id="sello"></div>
  <div class="ayuda-herramienta" id="ayuda"></div>
  <div class="cajetin">
    <div class="titulo">LW-SIM-02 · MESA DE MONTAJE</div>
    <div class="k">FÍSICA</div><div id="m-hz">— Hz</div>
    <div class="k">PUBLICACIÓN</div><div id="m-pub">— Hz</div>
    <div class="k">NAVEGADOR</div><div id="m-fps">— FPS</div>
    <div class="k">ROBOT</div><div id="m-pol">guion</div>
    <div class="k">ESCALA</div><div>1:1 · mm</div>
  </div>`;

const panel = $("#panel");
panel.innerHTML = `
  <div class="grupo ancho">
    <h2>ÓRDENES A CHISPAS · VOZ O TEXTO</h2>
    <div class="fila">
      <button class="boton micro" id="b-micro">🎙 HABLAR</button>
      <input class="texto-orden" id="t-orden" placeholder="«móntame una esquina»" />
      <button class="boton" id="b-enviar">ENVIAR</button>
    </div>
    <div class="tarjeta" id="tarjeta" hidden>
      <div class="oido" id="tarjeta-oido"></div>
      <div id="tarjeta-pregunta"></div>
      <div class="fila" id="tarjeta-botones" style="margin-top:6px"></div>
    </div>
  </div>
  <div class="grupo">
    <h2>ATAJOS · ORDEN CONFIRMADA</h2>
    <div class="fila">
      <button class="boton primario" data-jugar>▶ JUGAR</button>
      <button class="boton" data-orden="monta una unión en T">MONTA T</button>
      <button class="boton" data-orden="monta una unión en esquina">MONTA ESQUINA</button>
      <button class="boton" data-orden="señala el cordón">SEÑALA</button>
      <button class="boton" data-orden="coge la antorcha y suelda la junta">SUELDA</button>
      <button class="boton" data-orden="desmonta la junta">DESMONTA</button>
      <button class="boton" data-orden="acércame la antorcha">ANTORCHA</button>
    </div>
  </div>
  <div class="grupo">
    <h2>HERRAMIENTA DEL RATÓN</h2>
    <div class="fila" id="herramientas">
      <button class="boton" data-h="camara">1 · CÁMARA</button>
      <button class="boton" data-h="antorcha">2 · ANTORCHA</button>
      <button class="boton" data-h="base">3 · BASE</button>
      <button class="boton" data-h="chapa">4 · CHAPA</button>
    </div>
    <div class="medidas" style="margin-top:8px">
      <span class="k">TRABAJO</span><span id="v-trabajo">45°</span>
      <span class="k">AVANCE</span><span id="v-avance">10°</span>
      <span class="k">ALTURA PUNTA</span><span id="v-altura">0,5 mm</span>
      <span class="k">GATILLO · APOYO</span><span id="v-gatillo">—</span>
    </div>
  </div>
  <div class="grupo">
    <h2>PERTURBACIONES · COMO EN LA COMPETICIÓN</h2>
    <div class="fila">
      <button class="boton" id="b-girar">GIRAR BASE 90°</button>
      <button class="boton" id="b-lejos">BASE LEJOS</button>
      <button class="boton" id="b-base0">BASE A SU SITIO</button>
      <button class="boton" id="b-chapa-azar">CHAPA AL AZAR</button>
      <button class="boton" id="b-mano-t">MONTO YO · T</button>
      <button class="boton" id="b-mano-e">MONTO YO · ESQ.</button>
    </div>
  </div>
  <div class="grupo">
    <h2>RONDA · WEBCAMS · DEMO</h2>
    <div class="fila">
      <button class="boton" id="b-terminar">TERMINAR RONDA</button>
      <input class="texto-orden" id="t-ini" maxlength="3" placeholder="ABC" style="max-width:64px;text-transform:uppercase" />
      <button class="boton" id="b-firmar">FIRMAR</button>
      <button class="boton" data-cam="a">WEBCAM A</button>
      <button class="boton" data-cam="b">WEBCAM B</button>
      <button class="boton primario" id="b-jurado">DEMO JURADO</button>
      <button class="boton peligro" id="b-reiniciar">REINICIAR</button>
    </div>
  </div>
  <div class="grupo ancho">
    <h2>REGISTRO</h2>
    <div class="registro" id="registro"></div>
  </div>`;

function registrar(texto) {
  const r = $("#registro");
  const d = document.createElement("div");
  d.textContent = `${new Date().toLocaleTimeString("es-ES")} · ${texto}`;
  r.prepend(d);
  while (r.children.length > 40) r.lastChild.remove();
}

// --- three.js ----------------------------------------------------------------------------------------------------
const lienzo = $("#lienzo");
const renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const escena = new THREE.Scene();
const camara = new THREE.PerspectiveCamera(38, 1, 5, 6000);
camara.up.set(0, 0, 1);
escena.add(new THREE.AmbientLight(0xffffff, 1.6));
const sol = new THREE.DirectionalLight(0xffffff, 1.6);
sol.position.set(-300, -500, 900);
escena.add(sol);

// Órbita mínima (sin OrbitControls en vendor): esféricas alrededor de un objetivo.
const orbita = { objetivo: new THREE.Vector3(190, -30, 40), dist: 920, az: -1.2, el: 0.6 };
function aplicarOrbita() {
  const { objetivo: o, dist: d, az, el } = orbita;
  camara.position.set(o.x + d * Math.cos(el) * Math.cos(az), o.y + d * Math.cos(el) * Math.sin(az), o.z + d * Math.sin(el));
  camara.lookAt(o);
}
aplicarOrbita();

function redimensionar() {
  const w = mesaEl.clientWidth, h = mesaEl.clientHeight;
  renderer.setSize(w, h, false);
  camara.aspect = w / h;
  camara.updateProjectionMatrix();
}
new ResizeObserver(redimensionar).observe(mesaEl);
redimensionar();

// Materiales de plano: relleno azul translúcido + aristas claras.
function conAristas(geo, { relleno = COL.relleno, opacidad = 0.55, arista = COL.trazo, umbral = 25, aristaOpacidad = 0.9 } = {}) {
  const g = new THREE.Group();
  const malla = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: relleno, transparent: true, opacity: opacidad,
    side: THREE.DoubleSide, depthWrite: opacidad > 0.5 }));
  const aristas = new THREE.LineSegments(new THREE.EdgesGeometry(geo, umbral),
    new THREE.LineBasicMaterial({ color: arista, transparent: true, opacity: aristaOpacidad }));
  g.add(malla, aristas);
  g.userData.malla = malla;
  return g;
}

// Mesa: tablero, rejilla, robot... (todo en mm)
const tablero = new THREE.Mesh(new THREE.PlaneGeometry(1200, 800),
  new THREE.MeshBasicMaterial({ color: 0x0c3a6c, transparent: true, opacity: 0.5 }));
tablero.position.set(200, 0, -0.5);
escena.add(tablero);
const rejilla = new THREE.GridHelper(1200, 24, 0x7fa6cf, 0x2f5f92);
rejilla.rotation.x = Math.PI / 2;
rejilla.position.set(200, 0, 0);
rejilla.material.transparent = true; rejilla.material.opacity = 0.35;
escena.add(rejilla);
const rejillaFina = new THREE.GridHelper(1200, 120, 0x1f4f82, 0x1f4f82);
rejillaFina.rotation.x = Math.PI / 2;
rejillaFina.position.set(200, 0, -0.2);
rejillaFina.material.transparent = true; rejillaFina.material.opacity = 0.25;
escena.add(rejillaFina);
const borde = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.PlaneGeometry(1200, 800)),
  new THREE.LineBasicMaterial({ color: COL.trazo2 }));
borde.position.set(200, 0, 0);
escena.add(borde);
// ejes de la mesa
function linea(puntos, color, { discontinua = false, opacidad = 1, ancho = 1 } = {}) {
  const geo = new THREE.BufferGeometry().setFromPoints(puntos.map((p) => new THREE.Vector3(...p)));
  const mat = discontinua ? new THREE.LineDashedMaterial({ color, dashSize: 6, gapSize: 4, transparent: true, opacity: opacidad })
    : new THREE.LineBasicMaterial({ color, transparent: true, opacity: opacidad, linewidth: ancho });
  const l = new THREE.Line(geo, mat);
  if (discontinua) l.computeLineDistances();
  return l;
}
escena.add(linea([[0, 0, 0.3], [120, 0, 0.3]], COL.rojo, { opacidad: 0.8 }));
escena.add(linea([[0, 0, 0.3], [0, 120, 0.3]], COL.verde, { opacidad: 0.8 }));

// Etiquetas HTML que siguen puntos 3D
const etiquetas = [];
function etiqueta(texto, pos, clase = "") {
  const el = document.createElement("div");
  el.className = `etq ${clase}`;
  el.textContent = texto;
  $("#etiquetas").append(el);
  const e = { el, pos: new THREE.Vector3(...pos), visible: true };
  etiquetas.push(e);
  return e;
}
function pintarEtiquetas() {
  const w = mesaEl.clientWidth, h = mesaEl.clientHeight;
  for (const e of etiquetas) {
    const p = e.pos.clone().project(camara);
    const ok = e.visible && p.z < 1 && Math.abs(p.x) < 1.1 && Math.abs(p.y) < 1.1;
    e.el.style.display = ok ? "" : "none";
    if (ok) e.el.style.left = `${(p.x + 1) / 2 * w}px`, e.el.style.top = `${(1 - p.y) / 2 * h}px`;
  }
}
etiqueta("SO-101 · CHISPAS", [0, -60, 250]);

// --- mallas del servidor -----------------------------------------------------------------------------------------
const cuerposRobot = [];
const piezas = {};
async function cargarMallas() {
  const indice = await (await fetch("/api/mallas")).json();
  const blob = await (await fetch("/api/mallas.bin")).arrayBuffer();
  const geometria = (e) => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(blob, e.v[0], e.v[1] * 3), 3));
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(blob, e.f[0], e.f[1] * 3), 1));
    geo.computeVertexNormals();
    return geo;
  };
  for (let i = 0; i < indice.cuerpos.length; i++) {
    const g = new THREE.Group();
    g.matrixAutoUpdate = true;
    escena.add(g);
    cuerposRobot.push(g);
  }
  for (const e of indice.robot) {
    const color = new THREE.Color(e.rgba[0], e.rgba[1], e.rgba[2]);
    const relleno = color.clone().lerp(new THREE.Color(0x9cc6ef), 0.8);
    cuerposRobot[e.cuerpo].add(conAristas(geometria(e), { relleno, opacidad: 0.62, arista: COL.trazo, umbral: 35, aristaOpacidad: 0.5 }));
  }
  const p = indice.piezas;
  piezas.base = conAristas(geometria(p.base), { relleno: 0x2a6fb5, opacidad: 0.7 });
  piezas.chapa = conAristas(geometria(p.movil), { relleno: 0x5d9bdb, opacidad: 0.8 });
  piezas.antorcha = new THREE.Group();
  piezas.antorcha.add(conAristas(geometria(p.antorcha_a), { relleno: COL.arco, opacidad: 0.75, arista: COL.arcoClaro }));
  piezas.antorcha.add(conAristas(geometria(p.antorcha_b), { relleno: COL.arco, opacidad: 0.75, arista: COL.arcoClaro }));
  piezas.soporte = conAristas(geometria(p.soporte), { relleno: 0x24609e, opacidad: 0.6 });
  for (const k of ["base", "chapa", "antorcha", "soporte"]) escena.add(piezas[k]);
  // LED de la antorcha del robot (en la punta: origen del marco de la antorcha)
  piezas.led = new THREE.Mesh(new THREE.SphereGeometry(4, 16, 12), new THREE.MeshBasicMaterial({ color: 0x6dffb0 }));
  piezas.antorcha.add(piezas.led);
  piezas.luzLed = new THREE.PointLight(0x9dffcf, 0, 220);
  piezas.antorcha.add(piezas.luzLed);
}

// --- elementos fijos de la escena (al recibir `escena`) ---------------------------------------------------------
let datosEscena = null;
const grupoFijo = new THREE.Group();
escena.add(grupoFijo);
function montarEscena(e) {
  datosEscena = e;
  grupoFijo.clear();
  const z = e.zona_libre;
  // la zona libre: rectángulo discontinuo donde cae el centro de la chapa tumbada
  const [x0, x1] = z.x, [y0, y1] = z.y;
  grupoFijo.add(linea([[x0, y0, 0.4], [x1, y0, 0.4], [x1, y1, 0.4], [x0, y1, 0.4], [x0, y0, 0.4]], COL.arcoClaro, { discontinua: true }));
  etiqueta("ZONA LIBRE", [(x0 + x1) / 2, y0 - 6, 1]);
  etiqueta("SOPORTE ANTORCHA", [e.soporte.x, e.soporte.y, 150]);
  for (const [nombre, cam] of Object.entries(e.camaras)) {
    const o = new THREE.Vector3(...cam.origen), obj = new THREE.Vector3(...cam.objetivo);
    const dir = obj.clone().sub(o);
    const largo = dir.length() * 1.05;
    dir.normalize();
    const derecha = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 0, 1)).normalize();
    const arriba = new THREE.Vector3().crossVectors(derecha, dir).normalize();
    const th = Math.tan(THREE.MathUtils.degToRad(cam.fov_h / 2)), tv = th / cam.aspecto;
    const esquinas = [[1, 1], [-1, 1], [-1, -1], [1, -1]].map(([a, b]) => {
      const r = dir.clone().add(derecha.clone().multiplyScalar(a * th)).add(arriba.clone().multiplyScalar(b * tv));
      const k = r.z < -1e-3 ? Math.min(-o.z / r.z, largo * 2) : largo; // hasta el tablero
      return o.clone().addScaledVector(r, k);
    });
    const pts = [];
    for (const q of esquinas) pts.push(o, q);
    for (let i = 0; i < 4; i++) pts.push(esquinas[i], esquinas[(i + 1) % 4]);
    const cono = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineDashedMaterial({ color: COL.cian, dashSize: 10, gapSize: 7, transparent: true, opacity: 0.4 }));
    cono.computeLineDistances();
    grupoFijo.add(cono);
    // la propia webcam: una cajita
    const caja = conAristas(new THREE.BoxGeometry(40, 28, 22), { relleno: 0x0f4479, opacidad: 0.15, arista: COL.cian });
    caja.position.copy(o);
    caja.lookAt(obj);
    grupoFijo.add(caja);
    grupoFijo.add(linea([[o.x, o.y, o.z], [o.x, o.y, 0]], COL.trazo3, { discontinua: true, opacidad: 0.6 }));
    etiqueta(`WEBCAM ${nombre.toUpperCase()}`, [o.x, o.y, o.z + 30]);
  }
}

// --- estado dinámico ---------------------------------------------------------------------------------------------
let mundo = null;
const qTmp = new THREE.Quaternion();
function poseDe(obj, p, q) {
  obj.position.set(p[0], p[1], p[2]);
  obj.quaternion.set(q[1], q[2], q[3], q[0]);
}
function giroBase(b) {
  const g = THREE.MathUtils.degToRad(b.giro + 90);
  return [Math.cos(g / 2), 0, 0, Math.sin(g / 2)];
}
// cordón: línea discontinua de la junta reconocida
const cordonLinea = linea([[0, 0, 0], [120, 0, 0]], COL.cian, { discontinua: true });
cordonLinea.visible = false;
escena.add(cordonLinea);
let cordon = null; // {o: Vector3, R: Matrix4}
function deCordon(x, y, z) {
  if (!cordon) return null;
  return new THREE.Vector3(x, y, z).applyMatrix4(cordon.m);
}

// trazas: juez (por calidad) y robot (fantasma)
function crearTraza(max, colorBase) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(max * 3), 3));
  geo.setAttribute("color", new THREE.BufferAttribute(new Float32Array(max * 3), 3));
  geo.setDrawRange(0, 0);
  const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: 5, vertexColors: true, transparent: true, opacity: 0.95, sizeAttenuation: true }));
  pts.userData = { n: 0, max, colorBase };
  escena.add(pts);
  return pts;
}
const trazaJuez = crearTraza(6000);
const trazaRobot = crearTraza(6000);
trazaRobot.material.size = 4; trazaRobot.material.opacity = 0.7;
function anadirTraza(t, p, color) {
  const u = t.userData;
  if (u.n >= u.max || !p) return;
  t.geometry.attributes.position.setXYZ(u.n, p.x, p.y, p.z + 0.6);
  const c = new THREE.Color(color);
  t.geometry.attributes.color.setXYZ(u.n, c.r, c.g, c.b);
  u.n++;
  t.geometry.setDrawRange(0, u.n);
  t.geometry.attributes.position.needsUpdate = true;
  t.geometry.attributes.color.needsUpdate = true;
}
function vaciarTraza(t) { t.userData.n = 0; t.geometry.setDrawRange(0, 0); }

// antorcha del juez
const antorchaJuez = new THREE.Group();
{
  const cuerpo = conAristas(new THREE.CylinderGeometry(9, 8, 95, 24, 1), { relleno: 0xffd9a8, opacidad: 0.92, arista: COL.arco });
  cuerpo.rotation.x = Math.PI / 2; cuerpo.position.z = 68;
  const boquilla = conAristas(new THREE.CylinderGeometry(2.5, 6, 22, 16, 1), { relleno: 0xeaf3ff, opacidad: 0.95, arista: COL.trazo });
  boquilla.rotation.x = Math.PI / 2; boquilla.position.z = 11;
  const gatillo = conAristas(new THREE.BoxGeometry(7, 12, 16), { relleno: COL.rojo, opacidad: 0.95, arista: COL.trazo });
  gatillo.position.set(0, -13, 78);
  antorchaJuez.add(cuerpo, boquilla, gatillo);
}
const arco = new THREE.Mesh(new THREE.SphereGeometry(6, 16, 12), new THREE.MeshBasicMaterial({ color: 0xfff3dc, transparent: true, opacity: 0.95 }));
const luzArco = new THREE.PointLight(0xffa040, 0, 300);
antorchaJuez.add(arco, luzArco);
antorchaJuez.visible = false;
escena.add(antorchaJuez);
const etqJuez = etiqueta("JUEZ", [0, 0, 0], "caliente");
etqJuez.visible = false;

// chispas
const N_CHISPAS = 90;
const chispas = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ color: 0xffc56b, size: 3.2, transparent: true, opacity: 0.95 }));
chispas.geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(N_CHISPAS * 3), 3));
const velChispas = Array.from({ length: N_CHISPAS }, () => new THREE.Vector3());
const vidaChispas = new Float32Array(N_CHISPAS);
escena.add(chispas);
function emitirChispas(origen, dt) {
  const pos = chispas.geometry.attributes.position;
  for (let i = 0; i < N_CHISPAS; i++) {
    vidaChispas[i] -= dt;
    if (vidaChispas[i] <= 0 && origen && Math.random() < 0.5) {
      vidaChispas[i] = 0.25 + Math.random() * 0.35;
      pos.setXYZ(i, origen.x, origen.y, origen.z);
      velChispas[i].set((Math.random() - 0.5) * 260, (Math.random() - 0.5) * 260, 80 + Math.random() * 220);
    } else if (vidaChispas[i] > 0) {
      velChispas[i].z -= 900 * dt;
      pos.setXYZ(i, pos.getX(i) + velChispas[i].x * dt, pos.getY(i) + velChispas[i].y * dt, Math.max(0, pos.getZ(i) + velChispas[i].z * dt));
    } else {
      pos.setXYZ(i, 0, 0, -1000);
    }
  }
  pos.needsUpdate = true;
}

// --- herramientas del ratón ---------------------------------------------------------------------------------
const juez = { trabajo: 45, avance: 10, altura: 0.5, gatillo: false, punto: null, normal: null, sobre: false };
let herramienta = "camara";
const AYUDA = {
  camara: "<b>CÁMARA</b> · arrastrar: girar · mayús/botón central + arrastrar: desplazar · rueda: acercar",
  antorcha: "<b>ANTORCHA DEL JUEZ</b> · mover: la punta sigue la chapa · <b>botón izquierdo mantenido = gatillo</b> · rueda / Q-E: subir o bajar la punta (apoyo < 2 mm) · W/S: ángulo de trabajo · A/D: ángulo de avance · botón derecho: girar la cámara",
  base: "<b>BASE</b> · arrastrar: mover la base fija por la mesa · rueda: girarla 5° · R: girarla 90°",
  chapa: "<b>CHAPA</b> · clic: soltar la chapa móvil tumbada en ese punto · rueda: girarla 10°",
};
let giroChapa = 0;
function elegirHerramienta(h) {
  herramienta = h;
  document.querySelectorAll("[data-h]").forEach((b) => b.classList.toggle("activo", b.dataset.h === h));
  antorchaJuez.visible = h === "antorcha" || Boolean(mundo?.juez && herramienta !== "antorcha" && mundo.juez.gatillo);
  pintarAyuda();
}
document.querySelectorAll("[data-h]").forEach((b) => b.addEventListener("click", () => elegirHerramienta(b.dataset.h)));

function pintarAyuda() {
  let extra = "";
  if (herramienta === "antorcha") {
    const ap = juez.ultimaApoyada;
    extra = `<br>GATILLO <b>${juez.gatillo ? "PULSADO" : "suelto"}</b> · PUNTA a ${juez.altura.toFixed(1)} mm · ` +
      (ap == null ? "sin junta reconocida" : ap ? `<span class="apoyo-si">APOYADA</span>` : `<span class="apoyo-no">EN EL AIRE</span>`);
  }
  $("#ayuda").innerHTML = AYUDA[herramienta] + extra;
  $("#v-trabajo").textContent = `${juez.trabajo.toFixed(0)}°`;
  $("#v-avance").textContent = `${juez.avance.toFixed(0)}°`;
  $("#v-altura").textContent = `${juez.altura.toFixed(1).replace(".", ",")} mm`;
  $("#v-gatillo").textContent = `${juez.gatillo ? "PULSADO" : "suelto"} · ${juez.ultimaApoyada == null ? "—" : juez.ultimaApoyada ? "apoyada" : "en el aire"}`;
}

const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const planoMesa = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
function rayo(ev) {
  const r = lienzo.getBoundingClientRect();
  ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  raycaster.setFromCamera(ndc, camara);
}
function puntoMesa(ev) {
  rayo(ev);
  const p = new THREE.Vector3();
  return raycaster.ray.intersectPlane(planoMesa, p) ? p : null;
}
function puntoPiezas(ev) {
  rayo(ev);
  const objetivos = [piezas.base?.userData.malla, piezas.chapa?.userData.malla].filter(Boolean);
  const golpes = raycaster.intersectObjects(objetivos, false);
  if (golpes.length) {
    const g = golpes[0];
    const n = g.face.normal.clone().transformDirection(g.object.matrixWorld);
    return { p: g.point.clone(), n };
  }
  const p = puntoMesa(ev);
  return p ? { p, n: new THREE.Vector3(0, 0, 1) } : null;
}

let arrastre = null;
lienzo.addEventListener("contextmenu", (ev) => ev.preventDefault());
lienzo.addEventListener("pointerdown", (ev) => {
  lienzo.setPointerCapture(ev.pointerId);
  const orbitar = herramienta === "camara" || ev.button === 2 || ev.button === 1;
  if (orbitar) { arrastre = { tipo: ev.shiftKey || ev.button === 1 ? "desplazar" : "orbita", x: ev.clientX, y: ev.clientY }; return; }
  if (herramienta === "antorcha" && ev.button === 0) { juez.gatillo = true; enviarJuez(); pintarAyuda(); }
  if (herramienta === "base" && ev.button === 0 && mundo) {
    const p = puntoMesa(ev);
    if (p) arrastre = { tipo: "base", dx: mundo.base.x - p.x, dy: mundo.base.y - p.y };
  }
  if (herramienta === "chapa" && ev.button === 0) {
    const p = puntoMesa(ev);
    if (p) enviar({ orden: "soltar_chapa", x: p.x, y: p.y, giro: giroChapa }), registrar(`chapa soltada en (${p.x.toFixed(0)}, ${p.y.toFixed(0)}) a ${giroChapa}°`);
  }
});
lienzo.addEventListener("pointerup", (ev) => {
  if (herramienta === "antorcha" && ev.button === 0) { juez.gatillo = false; enviarJuez(); pintarAyuda(); }
  arrastre = null;
});
let ultimoBase = 0;
lienzo.addEventListener("pointermove", (ev) => {
  if (arrastre?.tipo === "orbita") {
    orbita.az -= (ev.clientX - arrastre.x) * 0.006;
    orbita.el = THREE.MathUtils.clamp(orbita.el + (ev.clientY - arrastre.y) * 0.005, 0.05, 1.5);
    arrastre.x = ev.clientX; arrastre.y = ev.clientY;
    aplicarOrbita();
    return;
  }
  if (arrastre?.tipo === "desplazar") {
    const k = orbita.dist / 900;
    const derecha = new THREE.Vector3().setFromMatrixColumn(camara.matrix, 0);
    const adelante = new THREE.Vector3(-Math.cos(orbita.az), -Math.sin(orbita.az), 0);
    orbita.objetivo.addScaledVector(derecha, -(ev.clientX - arrastre.x) * k).addScaledVector(adelante, (ev.clientY - arrastre.y) * k);
    arrastre.x = ev.clientX; arrastre.y = ev.clientY;
    aplicarOrbita();
    return;
  }
  if (arrastre?.tipo === "base" && performance.now() - ultimoBase > 60) {
    ultimoBase = performance.now();
    const p = puntoMesa(ev);
    if (p) enviar({ orden: "mover_base", x: p.x + arrastre.dx, y: p.y + arrastre.dy, giro: mundo.base.giro });
  }
  if (herramienta === "antorcha") {
    const g = puntoPiezas(ev);
    if (g) { juez.punto = g.p; juez.normal = g.n; }
  }
  if (herramienta === "chapa") {
    const p = puntoMesa(ev);
    if (p) fantasmaChapa(p);
  }
});
lienzo.addEventListener("pointerleave", () => { if (herramienta === "antorcha") { juez.gatillo = false; } });
lienzo.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  const s = Math.sign(ev.deltaY);
  if (herramienta === "antorcha" && !ev.ctrlKey) {
    juez.altura = THREE.MathUtils.clamp(juez.altura + (s > 0 ? 1 : -1) * (juez.altura < 3 ? 0.5 : 2), 0, 40);
    pintarAyuda();
  } else if (herramienta === "base" && mundo) {
    enviar({ orden: "mover_base", x: mundo.base.x, y: mundo.base.y, giro: mundo.base.giro + 5 * s });
  } else if (herramienta === "chapa") {
    giroChapa = ((giroChapa + 10 * s + 180) % 360 + 360) % 360 - 180;
  } else {
    orbita.dist = THREE.MathUtils.clamp(orbita.dist * (1 + 0.1 * s), 250, 3000);
    aplicarOrbita();
  }
}, { passive: false });
window.addEventListener("keydown", (ev) => {
  if (ev.target.tagName === "INPUT") return;
  const k = ev.key.toLowerCase();
  if ("1234".includes(k)) elegirHerramienta(["camara", "antorcha", "base", "chapa"][Number(k) - 1]);
  if (k === "w") juez.trabajo = Math.min(89, juez.trabajo + 5);
  if (k === "s") juez.trabajo = Math.max(5, juez.trabajo - 5);
  if (k === "d") juez.avance = Math.min(60, juez.avance + 5);
  if (k === "a") juez.avance = Math.max(-40, juez.avance - 5);
  if (k === "q") juez.altura = Math.min(40, juez.altura + 1);
  if (k === "e") juez.altura = Math.max(0, juez.altura - 1);
  if (k === " " && herramienta === "antorcha") { juez.gatillo = true; ev.preventDefault(); }
  if (k === "r" && mundo) enviar({ orden: "mover_base", x: mundo.base.x, y: mundo.base.y, giro: mundo.base.giro + 90 });
  pintarAyuda();
});
window.addEventListener("keyup", (ev) => { if (ev.key === " " && herramienta === "antorcha") { juez.gatillo = false; pintarAyuda(); } });

// silueta de la chapa a soltar (herramienta chapa)
const siluetaChapa = linea([[-70, -20, 0], [70, -20, 0], [70, 20, 0], [-70, 20, 0], [-70, -20, 0]], COL.arcoClaro, { discontinua: true });
siluetaChapa.visible = false;
escena.add(siluetaChapa);
function fantasmaChapa(p) {
  siluetaChapa.visible = true;
  siluetaChapa.position.set(p.x, p.y, 1);
  siluetaChapa.rotation.z = THREE.MathUtils.degToRad(giroChapa + 90);
}

// eje de la antorcha (dirección mango → punta) con los ángulos del contrato en el marco del cordón
function ejeAntorcha() {
  const t = THREE.MathUtils.degToRad(juez.trabajo), a = THREE.MathUtils.degToRad(juez.avance);
  const d = new THREE.Vector3(Math.tan(a), 1 / Math.tan(t), -1).normalize();
  if (cordon) d.applyMatrix3(new THREE.Matrix3().setFromMatrix4(cordon.m));
  else d.set(0, 0, -1);
  return d;
}
function puntaJuez() {
  if (!juez.punto) return null;
  const n = juez.normal || new THREE.Vector3(0, 0, 1);
  return juez.punto.clone().addScaledVector(n, juez.altura);
}
let ultimoEnvioJuez = 0;
function enviarJuez() {
  const p = puntaJuez();
  if (!p || herramienta !== "antorcha") return;
  ultimoEnvioJuez = performance.now();
  enviar({ orden: "antorcha_juez", p: [p.x, p.y, p.z], gatillo: juez.gatillo, trabajo: juez.trabajo, avance: juez.avance });
}

// --- conexión -----------------------------------------------------------------------------------------------------
let ws = null;
function enviar(o) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(o)); }
function conectar() {
  const url = new URL(conPartida("/ws_sim"), location.href);
  url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(url);
  ws.onopen = () => {
    registrar("conectado al simulador");
    if (params.get("guion")) enviar({ orden: "guion", nombre: params.get("guion"), bucle: params.has("bucle") });
  };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    (Array.isArray(m) ? m : [m]).forEach(recibir);
  };
  ws.onclose = () => { registrar("sin conexión: reintento"); setTimeout(conectar, 1000); };
}

let ultimaPantalla = null;
function recibir(m) {
  switch (m.tipo) {
    case "escena": {
      montarEscena(m);
      const el = $("#partida");
      if (m.modo_partidas === "por_pestana" && !m.compartida) {
        el.innerHTML = `PARTIDA <b>${m.partida}</b> · SOLO TUYA · tablet aparte: <a href="${conPartida("/tablet")}" target="_blank">/tablet?partida=${m.partida}</a>`;
      } else if (m.modo_partidas === "por_pestana") {
        el.innerHTML = `<span class="aviso">AFORO COMPLETO · PARTIDA COMPARTIDA</span>: todos los conectados mandan a la vez`;
      } else {
        el.innerHTML = `PARTIDA COMPARTIDA · ${m.conectados} conectado${m.conectados === 1 ? "" : "s"} · todos mandan`;
      }
      break;
    }
    case "mundo": alMundo(m); break;
    case "pantalla":
      $("#pantalla").textContent = `PANTALLA · ${m.nombre.toUpperCase().replace("_", " ")}`;
      if (m.nombre !== ultimaPantalla) registrar(`pantalla ${m.nombre}`);
      if (m.nombre !== "pedir") $("#tarjeta").hidden = true;
      if (m.nombre === "ronda") { vaciarTraza(trazaJuez); $("#hud-puntos").textContent = "0"; }
      if (m.nombre === "demostracion") vaciarTraza(trazaRobot);
      if (m.nombre === "ronda" && herramienta !== "antorcha" && !params.get("guion")) elegirHerramienta("antorcha");
      ultimaPantalla = m.nombre;
      break;
    case "personaje": bocadillo(m.frase); registrar(`Chispas: ${m.frase}`); break;
    case "orden_propuesta": tarjeta(m); break;
    case "junta": registrar(`junta: ${m.junta} ${m.posicion_soldeo || ""} (${Math.round((m.confianza || 0) * 100)} %)${m.motivo ? " · " + m.motivo : ""}`); break;
    case "alcance": registrar(m.llega ? "alcance: llega" : `alcance: NO llega · ${m.texto || ""}`); break;
    case "puntos":
      $("#hud-puntos").textContent = (m.total ?? 0).toLocaleString("es-ES");
      $("#hud-combo").textContent = `COMBO ×${m.multiplicador ?? 1} · RACHA ${m.combo ?? 0}`;
      if (m.evento) sello(m.evento);
      break;
    case "muestra": {
      if (m.gatillo && m.apoyada) anadirTraza(trazaJuez, deCordon(m.x, m.y, m.z), CALIDAD[m.calidad] || CALIDAD.bien);
      break;
    }
    case "resultado": $("#hud-puntos").textContent = (m.puntos ?? 0).toLocaleString("es-ES"); registrar(`resultado: ${m.puntos} puntos, nota ${m.nota} · robot ${m.puntos_robot ?? "—"}`); break;
    case "ranking": if (m.posicion_nueva) registrar(`ranking: puesto ${m.posicion_nueva}`); break;
    case "aviso_sim": registrar(m.texto); bocadillo(m.texto, "SIM"); break;
    case "error": registrar(`error: ${m.texto}`); break;
    default: break;
  }
}

let temporizadorBocadillo = 0;
function bocadillo(texto, quien = "CHISPAS") {
  $("#bocadillo b").textContent = quien;
  $("#bocadillo-texto").textContent = texto;
  $("#bocadillo").style.opacity = 1;
  clearTimeout(temporizadorBocadillo);
  temporizadorBocadillo = setTimeout(() => ($("#bocadillo").style.opacity = 0), 5000);
}
let temporizadorSello = 0;
function sello(ev) {
  const s = $("#sello");
  s.textContent = ev.texto;
  s.className = `sello visible ${ev.tipo}`;
  clearTimeout(temporizadorSello);
  temporizadorSello = setTimeout(() => s.classList.remove("visible"), 1300);
}

function alMundo(m) {
  mundo = m;
  if (cuerposRobot.length) m.cuerpos.forEach((c, i) => poseDe(cuerposRobot[i], c, c.slice(3)));
  if (piezas.base) {
    poseDe(piezas.base, [m.base.x, m.base.y, 6], giroBase(m.base));
    poseDe(piezas.chapa, m.chapa.p, m.chapa.q);
    poseDe(piezas.antorcha, m.antorcha.p, m.antorcha.q);
    poseDe(piezas.soporte, [datosEscena?.soporte.x ?? 150, datosEscena?.soporte.y ?? 170, 0], [1, 0, 0, 0]);
    piezas.led.material.color.set(m.led ? 0x6dffb0 : 0x1d4d3a);
    piezas.luzLed.intensity = m.led ? 4000 : 0;
    if (m.led) anadirTraza(trazaRobot, new THREE.Vector3(...m.antorcha.p), 0x74d6ff);
  }
  if (m.cordon) {
    const R = m.cordon.R;
    const M = new THREE.Matrix4().set(R[0], R[1], R[2], m.cordon.o[0], R[3], R[4], R[5], m.cordon.o[1], R[6], R[7], R[8], m.cordon.o[2], 0, 0, 0, 1);
    cordon = { m: M };
    cordonLinea.visible = true;
    cordonLinea.matrixAutoUpdate = false;
    cordonLinea.matrix.copy(M).multiply(new THREE.Matrix4().makeTranslation(0, 0, 0.8));
  } else {
    cordon = null;
    cordonLinea.visible = false;
  }
  $("#m-hz").textContent = `${(m.hz_fisica || 0).toFixed(0)} Hz`;
  $("#m-pub").textContent = `${(m.hz_publicacion || 0).toFixed(0)} Hz`;
  $("#m-pol").textContent = m.robot?.politica || "guion";
  const r = m.robot || {};
  $("#robot-texto").textContent = r.orden ? `CHISPAS · «${r.orden}» · ${(r.fase || "").toUpperCase()}` : "CHISPAS · EN REPOSO";
  $("#robot-barra").style.width = `${Math.round((r.orden ? r.progreso : 0) * 100)}%`;
  // juez remoto (guion o la otra ventana)
  if (herramienta !== "antorcha" && m.juez) {
    juez.remoto = m.juez;
  } else juez.remoto = null;
  if (m.juez) juez.ultimaApoyada = m.juez.apoyada;
}

// --- panel: órdenes ---------------------------------------------------------------------------------------------
function confirmar(orden) {
  enviar({ orden: "confirmar", si: true, orden_confirmada: orden });
  registrar(`orden confirmada: ${orden}`);
  $("#tarjeta").hidden = true;
}
document.querySelectorAll("[data-orden]").forEach((b) => b.addEventListener("click", () => confirmar(b.dataset.orden)));
$("[data-jugar]").addEventListener("click", () => enviar({ orden: "jugar" }));
function tarjeta(p) {
  $("#tarjeta").hidden = false;
  $("#tarjeta-oido").textContent = p.texto_oido ? `HE OÍDO «${p.texto_oido}»` : "";
  $("#tarjeta-pregunta").textContent = p.pregunta || p.orden || "";
  const cont = $("#tarjeta-botones");
  cont.innerHTML = "";
  const boton = (texto, fn, clase = "boton") => { const b = document.createElement("button"); b.className = clase; b.textContent = texto; b.onclick = fn; cont.append(b); };
  if (p.botones?.length) p.botones.forEach((b) => boton(b.etiqueta.toUpperCase(), () => confirmar(b.orden), "boton primario"));
  else if (p.orden) { boton("SÍ", () => confirmar(p.orden), "boton primario"); boton("NO", () => { $("#tarjeta").hidden = true; enviar({ orden: "confirmar", si: false }); }); }
}
async function interpretar(texto) {
  if (!texto.trim()) return;
  registrar(`juez: «${texto}»`);
  try {
    const r = await (await fetch(conPartida("/api/voz"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ texto }) })).json();
    if (r.respuesta) bocadillo(r.respuesta);
    if (r.confirmable) tarjeta({ texto_oido: texto, orden: r.orden, pregunta: r.pregunta });
    else if (r.aclaracion && r.botones?.length) tarjeta({ texto_oido: texto, pregunta: r.aclaracion, botones: r.botones });
  } catch (e) {
    enviar({ orden: "voz", texto });
  }
}
$("#b-enviar").addEventListener("click", () => { interpretar($("#t-orden").value); $("#t-orden").value = ""; });
$("#t-orden").addEventListener("keydown", (ev) => { if (ev.key === "Enter") { interpretar(ev.target.value); ev.target.value = ""; } });
$("#b-micro").addEventListener("click", () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { registrar("este navegador no reconoce voz: escribe la orden"); return; }
  const rec = new SR();
  rec.lang = "es-ES"; rec.interimResults = false; rec.maxAlternatives = 3;
  $("#b-micro").classList.add("escuchando");
  rec.onresult = (ev) => interpretar(ev.results[0][0].transcript);
  rec.onend = () => $("#b-micro").classList.remove("escuchando");
  rec.onerror = () => registrar("no te he oído bien");
  rec.start();
});

// --- panel: perturbaciones y demo -----------------------------------------------------------------------------
$("#b-girar").addEventListener("click", () => mundo && enviar({ orden: "mover_base", x: mundo.base.x, y: mundo.base.y, giro: mundo.base.giro + 90 }));
$("#b-lejos").addEventListener("click", () => enviar({ orden: "mover_base", x: 400, y: 120, giro: 60 }));
$("#b-base0").addEventListener("click", () => datosEscena && enviar({ orden: "mover_base", ...datosEscena.base_por_defecto }));
$("#b-chapa-azar").addEventListener("click", () => {
  if (!datosEscena) return;
  const z = datosEscena.zona_libre, r = (a) => a[0] + Math.random() * (a[1] - a[0]);
  enviar({ orden: "soltar_chapa", x: r(z.x), y: r(z.y), giro: r(z.giro) });
});
$("#b-mano-t").addEventListener("click", () => { enviar({ orden: "monto_yo" }); enviar({ orden: "montar_a_mano", junta: "t" }); });
$("#b-mano-e").addEventListener("click", () => { enviar({ orden: "monto_yo" }); enviar({ orden: "montar_a_mano", junta: "esquina" }); });
$("#b-terminar").addEventListener("click", () => enviar({ orden: "terminar" }));
$("#b-firmar").addEventListener("click", () => enviar({ orden: "iniciales", texto: $("#t-ini").value }));
$("#b-reiniciar").addEventListener("click", () => { vaciarTraza(trazaJuez); vaciarTraza(trazaRobot); enviar({ orden: "reiniciar" }); });
$("#b-jurado").addEventListener("click", () => enviar({ orden: "guion", nombre: "jurado" }));
document.querySelectorAll("[data-cam]").forEach((b) => b.addEventListener("click", () => {
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.innerHTML = `<div class="caja"><img src="${conPartida(`/api/webcam/${b.dataset.cam}.jpg`)}&t=${Date.now()}" alt="webcam"><div class="pie">WEBCAM ${b.dataset.cam.toUpperCase()} · render sintético (escena_sintetica) · clic para cerrar</div></div>`;
  modal.onclick = () => modal.remove();
  document.body.append(modal);
}));

// --- bucle --------------------------------------------------------------------------------------------------------
let tPrevio = performance.now(), nFotogramas = 0, tFps = performance.now();
function bucle(ahora) {
  const dt = Math.min(0.05, (ahora - tPrevio) / 1000);
  tPrevio = ahora;
  // antorcha del juez: la local (ratón) o la del servidor (guion del jurado / otra ventana)
  let punta = null, gatillo = false, apoyada = null, d = null;
  if (herramienta === "antorcha" && juez.punto) {
    punta = puntaJuez(); gatillo = juez.gatillo; apoyada = juez.ultimaApoyada; d = ejeAntorcha();
    if (performance.now() - ultimoEnvioJuez > 33) enviarJuez();
  } else if (juez.remoto) {
    punta = new THREE.Vector3(...juez.remoto.p); gatillo = juez.remoto.gatillo; apoyada = juez.remoto.apoyada;
    const t0 = juez.trabajo, a0 = juez.avance;
    juez.trabajo = juez.remoto.trabajo; juez.avance = juez.remoto.avance; d = ejeAntorcha(); juez.trabajo = t0; juez.avance = a0;
  }
  antorchaJuez.visible = Boolean(punta);
  etqJuez.visible = Boolean(punta);
  if (punta) {
    antorchaJuez.position.copy(punta);
    antorchaJuez.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, -1), d);
    etqJuez.pos.copy(punta).addScaledVector(d, -110);
    const suelda = gatillo && apoyada;
    arco.visible = gatillo;
    arco.material.color.set(suelda ? 0xfff3dc : 0x7fa6cf);
    arco.scale.setScalar(suelda ? 1 + 0.35 * Math.random() : 0.6);
    luzArco.intensity = suelda ? 9000 + 6000 * Math.random() : 0;
    emitirChispas(suelda ? punta : null, dt);
  } else emitirChispas(mundo?.led ? new THREE.Vector3(...mundo.antorcha.p) : null, dt);
  if (!punta && mundo?.led) emitirChispas(new THREE.Vector3(...mundo.antorcha.p), 0);
  renderer.render(escena, camara);
  pintarEtiquetas();
  nFotogramas++;
  if (ahora - tFps > 2000) {
    const fps = (nFotogramas * 1000) / (ahora - tFps);
    $("#m-fps").textContent = `${fps.toFixed(0)} FPS`;
    enviar({ orden: "fps", fps });
    window.lewelderSim.fps = fps;
    nFotogramas = 0; tFps = ahora;
  }
  requestAnimationFrame(bucle);
}

window.lewelderSim = { orbita, aplicarOrbita, elegirHerramienta, juez, enviar, get mundo() { return mundo; }, fps: null, listo: false };
elegirHerramienta(params.get("herramienta") || "camara");
await cargarMallas();
conectar();
window.lewelderSim.listo = true;
requestAnimationFrame(bucle);
