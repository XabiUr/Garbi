// LeWelder v2 · la recreativa en la tablet. Una sola página: recibe los mensajes del protocolo v2 (PROTOCOLO.md) y
// pinta la pantalla que toca. No sabe si habla con el servidor real (`cliente.js`, WebSocket /ws2) o con la maqueta
// (`maqueta.js`, `?maqueta=1`): las dos le dan un "transporte" con `enviar(orden)` y le pasan los mensajes a `recibir`.
import { crearGemelo } from "./gemelo.js";
import { crearSonido } from "./sonido.js";
import * as voz from "./voz.js";
import * as C from "./contrato.js";

const PANTALLAS = ["atraccion", "pedir", "montaje", "reconocer", "demostracion", "cuenta_atras", "ronda",
  "resultado", "iniciales", "ranking", "plan_b"];
const TITULOS = {
  atraccion: "Atracción", pedir: "Pedido de junta", montaje: "Montaje", reconocer: "Junta reconocida",
  demostracion: "Demostración", cuenta_atras: "Cuenta atrás", ronda: "Ronda", resultado: "Resultado",
  iniciales: "Firma del juez", ranking: "Lista de piezas", plan_b: "Plan B · montaje manual",
};
const FASES = ["buscando", "cogiendo", "girando", "encajando"];
const NOMBRE_JUNTA = { t: "UNIÓN EN T", esquina: "UNIÓN EN ESQUINA", incompleta: "JUNTA INCOMPLETA" };
const PEOR = { bien: 0, regular: 1, quemado: 2 };
const LETRAS = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ";

const $ = (s) => document.querySelector(s);
const lamina = $("#lamina");
const reducido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const fmt = (n) => Math.round(n).toLocaleString("es-ES");

// --- lámina a pantalla completa ----------------------------------------------------------------------------------
let escala = 1;
function ajustarLamina() {
  escala = Math.min(window.innerWidth / 1280, window.innerHeight / 800);
  lamina.style.transformOrigin = "50% 50%";
  lamina.style.transform = `translate(-50%, -50%) scale(${escala})`;
  gemelo?.ajustar(escala);
}

const gemelo = crearGemelo($("#lienzo"), $("#etiquetas3d"));
ajustarLamina();
window.addEventListener("resize", ajustarLamina);
const sonido = crearSonido();

// --- estado ------------------------------------------------------------------------------------------------------
const st = {
  pantalla: null,
  juntaTipo: "esquina",
  junta: null,
  puntos: { total: 0, combo: 0, multiplicador: 1 },
  totalMostrado: 0,
  ranking: { top: [] },
  fantasma: null,
  carrera: { t0: null, x: 0 },
  tramos: new Array(C.N_TRAMOS).fill(null),
  muestra: null,
  tMuestra: 0,
  sinApoyoDesde: null,
  iniciales: ["A", "A", "A"],
  letraActiva: 0,
  temporizadores: [],
  propuesta: null,
  personaje: { nombre: voz.PERSONAJE.nombre, voz: voz.PERSONAJE.voz },
};
let transporte = { enviar: () => {} };

function enviar(obj) {
  transporte.enviar(obj);
}
function despues(ms, fn) {
  const id = setTimeout(fn, ms);
  st.temporizadores.push(id);
  return id;
}

// --- tira de 24 tramos (cota de 0 a 120 mm con las marcas de la carrera) -----------------------------------------
function crearTira(el) {
  el.innerHTML = `<div class="tira-celdas">${"<i></i>".repeat(C.N_TRAMOS)}</div>
    <div class="tira-escala"><span>0</span><span>30</span><span>60</span><span>90</span><span>120 mm</span></div>
    <div class="tira-marca robot" hidden></div><div class="tira-marca juez" hidden></div>`;
  const celdas = [...el.querySelectorAll(".tira-celdas i")];
  const mR = el.querySelector(".tira-marca.robot"), mJ = el.querySelector(".tira-marca.juez");
  return {
    pintar(i, c) { if (celdas[i]) celdas[i].className = c || ""; },
    caliente(i, si) { celdas[i]?.classList.toggle("caliente", si); },
    todo(lista) { celdas.forEach((x, i) => (x.className = lista[i] || "")); },
    juez(x) { mJ.hidden = x == null; if (x != null) mJ.style.left = `${(x / C.LONGITUD_CORDON) * 100}%`; },
    robot(x) { mR.hidden = x == null; if (x != null) mR.style.left = `${(Math.min(x, C.LONGITUD_CORDON) / C.LONGITUD_CORDON) * 100}%`; },
  };
}
const tiraRonda = crearTira($("#tira-ronda"));
const tiraRes = crearTira($("#tira-res"));

// --- personaje ---------------------------------------------------------------------------------------------------
const CARAS = {
  alegre: { ojos: '<path d="M22 40q7-9 14 0M44 40q7-9 14 0"/>', boca: "M28 52q12 10 24 0" },
  chulo: { ojos: '<rect class="lleno" x="18" y="33" width="44" height="9" rx="2"/><path d="M18 37h-4M62 37h4"/>', boca: "M30 55q12 3 22-5" },
  picado: { ojos: '<path d="M18 29l15 7M62 29l-15 7"/><circle class="lleno" cx="28" cy="41" r="3.5"/><circle class="lleno" cx="52" cy="41" r="3.5"/>', boca: "M29 57q11-8 22 0" },
  sorprendido: { ojos: '<circle cx="28" cy="38" r="7"/><circle cx="52" cy="38" r="7"/><circle class="lleno" cx="28" cy="38" r="2.5"/><circle class="lleno" cx="52" cy="38" r="2.5"/>', boca: "M34 55a6 6 0 1 0 12 0a6 6 0 1 0-12 0" },
  serio: { ojos: '<rect class="lleno" x="22" y="36" width="12" height="5"/><rect class="lleno" x="46" y="36" width="12" height="5"/>', boca: "M30 55h20" },
};
const elPersonaje = $("#personaje");
let ocultarBocadillo = null;
function hablar({ frase, emocion = "alegre", nombre } = {}) {
  if (!frase) return;
  const cara = CARAS[emocion] || CARAS.alegre;
  elPersonaje.dataset.emocion = emocion;
  elPersonaje.querySelector(".ojos").innerHTML = cara.ojos;
  elPersonaje.querySelector(".c-boca").setAttribute("d", cara.boca);
  $("#p-nombre").textContent = `${(nombre || st.personaje.nombre).toUpperCase()} · SO-101`;
  $("#cj-robot").textContent = (nombre || st.personaje.nombre).toUpperCase();
  $("#p-frase").textContent = frase;
  elPersonaje.hidden = false;
  const b = elPersonaje.querySelector(".bocadillo");
  b.classList.remove("pop");
  void b.offsetWidth;
  b.classList.add("pop");
  const habla = voz.decir(frase, { silencio: sonido.silencio, personaje: st.personaje,
    alTerminar: () => elPersonaje.classList.remove("hablando") });
  elPersonaje.classList.toggle("hablando", habla);
  if (!habla) sonido.robot();
  clearTimeout(ocultarBocadillo);
  if (st.pantalla === "ronda" || st.pantalla === "cuenta_atras") {
    ocultarBocadillo = setTimeout(() => { elPersonaje.hidden = true; }, 3500);
  }
}

// --- sellos de revisión (eventos arcade) -------------------------------------------------------------------------
let nSello = 0;
function sello(texto, tipo = "bueno", { x, y, nota } = {}) {
  const el = document.createElement("div");
  el.className = `sello ${tipo}`;
  el.textContent = texto;
  if (nota) {
    const n = document.createElement("span");
    n.className = "nota-mano";
    n.textContent = nota;
    el.append(n);
  }
  const huecos = [[640, 300], [470, 380], [810, 360], [640, 420]];
  const [hx, hy] = huecos[nSello++ % huecos.length];
  el.style.left = `${x ?? hx}px`;
  el.style.top = `${y ?? hy}px`;
  el.style.rotate = `${(Math.random() * 16 - 8).toFixed(1)}deg`;
  const cont = $("#sellos");
  while (cont.children.length > 2) cont.firstChild.remove();
  cont.append(el);
  setTimeout(() => el.classList.add("fuera"), tipo === "epico" ? 1700 : 1150);
  setTimeout(() => el.remove(), tipo === "epico" ? 2050 : 1500);
}
function golpe(rojo = true) {
  if (rojo) {
    const d = $("#destello");
    d.classList.remove("activo");
    void d.offsetWidth;
    d.classList.add("activo");
  }
  if (!reducido()) {
    lamina.classList.remove("temblor");
    void lamina.offsetWidth;
    lamina.classList.add("temblor");
    setTimeout(() => lamina.classList.remove("temblor"), 360);
  }
}

// --- lista de piezas (ranking) -----------------------------------------------------------------------------------
function htmlBom(top, { desde = 0, hasta = 10, nueva = null, titulo = "Lista de piezas · ranking del día" } = {}) {
  const filas = [];
  for (let i = desde; i < hasta; i++) {
    const r = top[i];
    const cls = nueva === i + 1 ? ' class="nueva"' : "";
    if (!r) { filas.push(`<tr><td class="pos">${String(i + 1).padStart(2, "0")}</td><td class="ini">· · ·</td><td>—</td><td class="n">—</td></tr>`); continue; }
    const junta = r.junta === "t" ? "T" : r.junta === "esquina" ? "ESQUINA" : (r.junta || "—").toUpperCase();
    filas.push(`<tr${cls}><td class="pos">${String(i + 1).padStart(2, "0")}</td><td class="ini">${escapar(r.iniciales)}</td>` +
      `<td>${junta}</td><td class="n">${fmt(r.puntos)}</td></tr>`);
  }
  return `<table><caption>${titulo}<small>${fechaHoy()}</small></caption>
    <thead><tr><th>Nº</th><th>Iniciales</th><th>Junta</th><th style="text-align:right">Puntos</th></tr></thead>
    <tbody>${filas.join("")}</tbody></table>`;
}
function escapar(t) {
  return String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function fechaHoy() {
  const d = new Date();
  return `${String(d.getDate()).padStart(2, "0")}-${String(d.getMonth() + 1).padStart(2, "0")}-${d.getFullYear()}`;
}
let paginaBom = 0;
function pintarBomAtraccion() {
  const top = st.ranking.top || [];
  const paginas = top.length > 5 ? 2 : 1;
  const p = paginaBom % paginas;
  $("#bom-atr").innerHTML = htmlBom(top, { desde: p * 5, hasta: p * 5 + 5, titulo: "Ranking del día" });
}
setInterval(() => {
  if (st.pantalla !== "atraccion") return;
  paginaBom++;
  pintarBomAtraccion();
}, 5000);

// --- pantallas ---------------------------------------------------------------------------------------------------
const AL_ENTRAR = {
  atraccion() {
    gemelo.visible(true);
    gemelo.carrera(false);
    gemelo.punta(null);
    gemelo.fantasma(null);
    gemelo.objetivoPlanB(false);
    gemelo.ejeCordon(false);
    gemelo.atraccion(true);
    gemelo.vista("iso", { alto: 300, centro: [0.76, 0.42], giro: 7 });
    gemelo.cotas(["base", "alto"]);
    paginaBom = 0;
    pintarBomAtraccion();
    $("#cj-juez").textContent = "— — —";
    $("#cj-junta").textContent = "—";
    sonido.musica(true);
  },
  pedir() {
    gemelo.atraccion(false);
    gemelo.visible(false);
    $("#confirmar").hidden = true;
    estadoMicro("TOCA Y HABLA");
  },
  montaje() {
    gemelo.atraccion(false);
    gemelo.visible(true);
    gemelo.objetivoPlanB(false);
    gemelo.punta(null);
    gemelo.fantasma(null);
    gemelo.antorchaRobot(null);
    gemelo.ejeCordon(false);
    gemelo.junta(st.juntaTipo);
    gemelo.cordonVacio();
    gemelo.montaje(0, { inmediato: true });
    gemelo.trazar(1.4);
    gemelo.vista("iso", { alto: 440, centro: [0.67, 0.56], giro: 0 });
    gemelo.cotas([]);
    $("#montaje-titulo").textContent = st.juntaTipo === "t" ? "MONTANDO UNA T" : "MONTANDO UNA ESQUINA";
    pintarFases(null, 0);
    $("#detalle").hidden = true;
  },
  reconocer() {
    gemelo.atraccion(false);
    gemelo.visible(true);
    gemelo.objetivoPlanB(false);
    gemelo.montaje(1);
    gemelo.antorchaRobot(null);
    gemelo.vista("iso", { alto: 300, centro: [0.31, 0.53], giro: 0, dur: 0.9 });
    gemelo.cotas(["base", "ancho", "cordon", "alto"]);
    gemelo.ejeCordon(true);
    // del isométrico al perfil (se ve la sección de la junta con su cordón) y vuelta
    // en el perfil se ve la sección del cordón (a4) en cian, como en el símbolo ISO 2553
    despues(4200, () => {
      gemelo.vista("perfil", { alto: 150, centro: [0.3, 0.6], dur: 1.2 });
      gemelo.cotas(["alto"]);
      for (let i = 0; i < C.N_TRAMOS; i++) gemelo.pintar(i, "guia");
    });
    despues(8200, () => {
      gemelo.vista("iso", { alto: 300, centro: [0.31, 0.53], giro: 6, dur: 1.2 });
      gemelo.cotas(["base", "ancho", "cordon", "alto"]);
      gemelo.cordonVacio();
    });
    if (st.junta) pintarJunta(st.junta);
  },
  demostracion() {
    gemelo.atraccion(false);
    gemelo.visible(true);
    gemelo.montaje(1, { inmediato: true });
    gemelo.cordonVacio();
    gemelo.cotas(["cordon"]);
    gemelo.ejeCordon(true);
    gemelo.antorchaRobot(0);
    gemelo.fantasma(0, { etiqueta: true });
    gemelo.vista("trabajo", { alto: 230, centro: [0.46, 0.5], giro: 0 });
    pintarDemo(0);
  },
  cuenta_atras() {
    gemelo.visible(true);
    gemelo.antorchaRobot(null);
    gemelo.cotas([]);
    gemelo.fantasma(0);
    gemelo.cordonVacio();
    gemelo.vista("trabajo", { alto: 210, centro: [0.5, 0.52] });
    cuentaAtras();
  },
  ronda() {
    gemelo.visible(true);
    gemelo.atraccion(false);
    gemelo.montaje(1, { inmediato: true });
    gemelo.antorchaRobot(null);
    gemelo.cotas([]);
    gemelo.ejeCordon(true);
    gemelo.carrera(true);
    gemelo.fantasma(0);
    gemelo.vista("trabajo", { alto: 210, centro: [0.5, 0.5], dur: 0.6 });
    st.carrera = { t0: null, x: 0 };
    st.tramos.fill(null);
    st.muestra = null;
    st.puntos = { total: 0, combo: 0, multiplicador: 1 };
    st.totalMostrado = 0;
    gemelo.cordonVacio();
    tiraRonda.todo([]);
    tiraRonda.juez(null);
    tiraRonda.robot(0);
    pintarPuntos(st.puntos);
    $("#carrera-quien").textContent = "—";
    $("#carrera-quien").className = "carrera-quien";
    $("#carrera-dif").textContent = "salís a la vez";
    $("#aviso-apoyo").hidden = true;
    elPersonaje.hidden = true;
  },
  resultado() {
    gemelo.visible(true);
    gemelo.carrera(false);
    gemelo.punta(null);
    gemelo.fantasma(C.LONGITUD_CORDON);
    gemelo.cotas([]);
    gemelo.vista("iso", { alto: 400, centro: [0.72, 0.56], giro: 6 });
    sonido.arco(false);
  },
  iniciales() {
    gemelo.visible(false);
    st.letraActiva = 0;
    pintarLetras();
    $("#ini-puntos").textContent = fmt(st.resultado?.puntos ?? st.puntos.total);
    st.resultado = null;
  },
  ranking() {
    gemelo.visible(true);
    gemelo.atraccion(false);
    gemelo.punta(null);
    gemelo.carrera(false);
    gemelo.vista("iso", { alto: 380, centro: [0.83, 0.4], giro: 6 });
    gemelo.cotas([]);
    pintarRanking();
  },
  plan_b() {
    gemelo.atraccion(false);
    gemelo.visible(true);
    gemelo.junta(st.juntaTipo);
    gemelo.cordonVacio();
    gemelo.montaje(0, { inmediato: true });
    gemelo.objetivoPlanB(true);
    gemelo.punta(null);
    gemelo.fantasma(null);
    gemelo.antorchaRobot(null);
    gemelo.cotas(["base"]);
    gemelo.vista("iso", { alto: 460, centro: [0.66, 0.5], giro: 0 });
    $("#b-donde").textContent = st.juntaTipo === "t" ? "en la línea central de la base" : "en el canto de la base";
  },
};

function irA(nombre) {
  if (!PANTALLAS.includes(nombre)) return;
  if (nombre === st.pantalla) return;
  st.temporizadores.forEach(clearTimeout);
  st.temporizadores = [];
  if (st.pantalla === "atraccion") sonido.musica(false);
  if (st.pantalla === "ronda") { sonido.arco(false); $("#aviso-apoyo").hidden = true; }
  st.pantalla = nombre;
  lamina.dataset.pantalla = nombre;
  const sec = document.querySelector(`.pantalla[data-p="${nombre}"]`);
  sec.classList.remove("entrando");
  void sec.offsetWidth;
  sec.classList.add("entrando");
  const barrido = $("#barrido");
  barrido.classList.remove("activo");
  void barrido.offsetWidth;
  barrido.classList.add("activo");
  sonido.barrido();
  $("#cj-titulo").textContent = TITULOS[nombre];
  $("#cj-hoja").textContent = `${PANTALLAS.indexOf(nombre) + 1}/${PANTALLAS.length}`;
  if (nombre !== "ronda" && nombre !== "cuenta_atras") clearTimeout(ocultarBocadillo);
  AL_ENTRAR[nombre]?.();
}

// --- pedir: micrófono, ejemplos y confirmación -------------------------------------------------------------------
function estadoMicro(texto, oido = false) {
  const e = $("#micro-estado");
  e.textContent = texto;
  e.classList.toggle("oido", oido);
}
let escucha = null;
$("#b-micro").addEventListener("click", () => {
  sonido.toque();
  if (escucha) { escucha.parar(); return; }
  if (!voz.hayReconocimiento && !transporte.simularVoz) {
    estadoMicro("SIN MICRO: TOCA UN EJEMPLO");
    return;
  }
  $("#b-micro").classList.add("escuchando");
  estadoMicro("TE ESCUCHO…");
  escucha = transporte.simularVoz ? transporte.simularVoz((t) => estadoMicro(`«${t}»`, true))
    : voz.escuchar((t) => estadoMicro(`«${t}»`, true));
  escucha.then(({ texto, alternativas }) => procesarFrase(texto, alternativas))
    .catch((e) => {
      const m = e.message;
      estadoMicro(m === "not-allowed" || m === "service-not-allowed" ? "SIN PERMISO DE MICRO: TOCA UN EJEMPLO"
        : m === "no-speech" ? "NO TE HE OÍDO · OTRA VEZ" : "NO TE HE OÍDO BIEN · OTRA VEZ");
    })
    .finally(() => { escucha = null; $("#b-micro").classList.remove("escuchando"); });
});
for (const b of document.querySelectorAll(".ejemplo")) {
  b.addEventListener("click", () => { sonido.toque(); procesarFrase(b.dataset.voz, []); });
}

async function procesarFrase(texto, alternativas = []) {
  estadoMicro(`«${texto}»`, true);
  let interp = null;
  try {
    interp = transporte.interpretar ? await transporte.interpretar(texto, alternativas)
      : await voz.interpretar(texto, alternativas, { pantalla: st.pantalla });
  } catch (e) {
    // sin /api/voz: que el servidor la interprete y conteste con `orden_propuesta`
    enviar({ orden: "voz", texto });
    return;
  }
  if (interp.personaje) st.personaje = interp.personaje;
  if (interp.respuesta) hablar({ frase: interp.respuesta, emocion: interp.confirmable ? "alegre" : "sorprendido" });
  if (interp.confirmable) {
    proponer({ texto_oido: texto, orden: interp.orden, pregunta: interp.pregunta });
  } else if (interp.aclaracion && interp.botones?.length) {
    proponer({ texto_oido: texto, orden: null, pregunta: interp.aclaracion, botones: interp.botones });
  } else {
    estadoMicro("NO TE HE ENTENDIDO · OTRA VEZ");
    sonido.error();
  }
}

function proponer(p) {
  st.propuesta = p;
  $("#conf-oido").textContent = `«${p.texto_oido || ""}»`;
  $("#conf-orden").textContent = p.orden || "—";
  $("#conf-pregunta").textContent = p.pregunta || `¿${p.orden}?`;
  const cont = document.querySelector(".conf-botones");
  if (p.botones?.length) {
    cont.innerHTML = "";
    for (const b of p.botones) {
      const btn = document.createElement("button");
      btn.className = "boton boton-si";
      btn.textContent = b.etiqueta.toUpperCase();
      btn.onclick = () => proponer({ texto_oido: p.texto_oido, orden: b.orden, pregunta: b.pregunta });
      cont.append(btn);
    }
  } else {
    cont.innerHTML = `<button class="boton boton-si" id="b-si">SÍ, ¡MÓNTALA!</button><button class="boton boton-no" id="b-no">NO, REPITE</button>`;
    $("#b-si").textContent = /monta/.test(p.orden || "") ? "SÍ, ¡MÓNTALA!" : "SÍ, ¡VALE!";
    $("#b-si").onclick = () => confirmar(true);
    $("#b-no").onclick = () => confirmar(false);
  }
  if (st.pantalla !== "pedir") irA("pedir");
  $("#confirmar").hidden = false;
  sonido.aviso();
}
function confirmar(si) {
  sonido.toque();
  const p = st.propuesta;
  $("#confirmar").hidden = true;
  if (si && p?.orden) {
    if (/esquina/.test(p.orden)) st.juntaTipo = "esquina";
    else if (/ en T/.test(p.orden)) st.juntaTipo = "t";
    $("#cj-junta").textContent = st.juntaTipo === "t" ? "En T" : "En esquina";
    estadoMicro("¡MARCHANDO!");
  } else {
    estadoMicro("TOCA Y HABLA");
  }
  enviar({ orden: "confirmar", si: Boolean(si && p?.orden), ...(p?.orden ? { orden_confirmada: p.orden } : {}) });
  st.propuesta = null;
}

// --- montaje -----------------------------------------------------------------------------------------------------
function pintarFases(fase, progreso) {
  const i = FASES.indexOf(fase);
  document.querySelectorAll("#fases li").forEach((li, j) => {
    li.classList.toggle("hecha", i > j || progreso >= 1);
    li.classList.toggle("actual", i === j && progreso < 1);
  });
  const barra = $("#montaje-barra");
  barra.querySelector(".cota-relleno").style.scale = `${Math.max(0, Math.min(1, progreso))} 1`;
  barra.querySelector(".cota-pct").textContent = `${Math.round(progreso * 100)} %`;
}

// --- reconocer ---------------------------------------------------------------------------------------------------
function pintarJunta(j) {
  const tipo = j.junta;
  $("#sj-nombre").textContent = NOMBRE_JUNTA[tipo] || String(tipo).toUpperCase();
  $("#sj-conf").textContent = j.confianza != null ? `${Math.round(j.confianza * 100)} %` : "";
  $("#sj-pos").textContent = j.posicion_soldeo || "—";
  $("#sj-pos-txt").textContent = C.POSICIONES_SOLDEO[j.posicion_soldeo] || "";
  document.querySelector(".iso2553 .pos").textContent = j.posicion_soldeo || "";
  const f = j.ficha || {};
  $("#ficha-para").textContent = f.para_que || "—";
  $("#ficha-donde").textContent = f.donde_se_usa || "—";
  $("#ficha-angulo").textContent = f.angulo || `${C.ANGULO_TRABAJO_OBJETIVO[tipo] ?? 45}° de trabajo, 0-20° de empuje`;
  $("#simbolo").hidden = tipo === "incompleta";
  $("#ficha").hidden = tipo === "incompleta";
  if (tipo === "incompleta") {
    $("#sj-pos").textContent = "¡OJO!";
    $("#sj-pos-txt").textContent = j.motivo || "la chapa no ha cerrado la junta";
  }
  if (tipo === "t" || tipo === "esquina") {
    st.juntaTipo = tipo;
    gemelo.junta(tipo);
    $("#cj-junta").textContent = tipo === "t" ? "En T" : "En esquina";
  }
}
function pintarAlcance(a) {
  $("#alcance").hidden = a.llega;
  $("#alcance-ok").hidden = !a.llega;
  if (!a.llega) {
    $("#alcance-texto").textContent = (a.texto || `gírala ${a.giro_grados ?? 90}° hacia mí`).toUpperCase();
    sonido.aviso();
  }
}
// Línea de referencia del símbolo ISO 2553: de la flecha del símbolo al cordón del gemelo.
function lineaReferencia() {
  const g = $("#guias");
  if (st.pantalla !== "reconocer" || $("#simbolo").hidden) { if (g.firstChild) g.innerHTML = ""; return; }
  const p = gemelo.puntoCordon(C.LONGITUD_CORDON * 0.62);
  // extremo izquierdo de la línea de referencia del símbolo (viewBox 360x120 dibujado a 380x127)
  const sx = 1280 - 60 - 380 + 20 * (380 / 360), sy = 236 + 70 * (127 / 120);
  const codo = sx - 40;
  g.innerHTML = `<path d="M${sx} ${sy} L${codo} ${sy} L${p.x.toFixed(1)} ${p.y.toFixed(1)}" fill="none" stroke="#eef6ff" stroke-width="2.5"/>
    <path d="M${p.x.toFixed(1)} ${p.y.toFixed(1)} l${flecha(codo - p.x, sy - p.y)}" fill="#eef6ff" stroke="#eef6ff" stroke-width="2" stroke-linejoin="round"/>`;
}
function flecha(dx, dy) {
  const l = Math.hypot(dx, dy) || 1;
  const ux = dx / l, uy = dy / l, s = 18, w = 6;
  const bx = ux * s, by = uy * s;
  return `${(bx - uy * w).toFixed(1)} ${(by + ux * w).toFixed(1)} l${(2 * uy * w).toFixed(1)} ${(-2 * ux * w).toFixed(1)}z`;
}

// --- demostración ------------------------------------------------------------------------------------------------
function pintarDemo(progreso) {
  const x = progreso * C.LONGITUD_CORDON;
  gemelo.antorchaRobot(progreso < 1 ? x : null);
  gemelo.fantasma(x, { etiqueta: true });
  const barra = $("#demo-barra");
  barra.querySelector(".cota-relleno").style.scale = `${progreso} 1`;
  barra.querySelector(".cota-pct").textContent = `${Math.round(x)} mm`;
}

// --- cuenta atrás ------------------------------------------------------------------------------------------------
function cuentaAtras() {
  const el = $("#cuenta");
  const poner = (t, suelda = false) => {
    el.textContent = t;
    el.classList.toggle("suelda", suelda);
    el.classList.remove("golpe");
    void el.offsetWidth;
    el.classList.add("golpe");
  };
  poner("3"); sonido.cuenta();
  despues(1000, () => { poner("2"); sonido.cuenta(); });
  despues(2000, () => { poner("1"); sonido.cuenta(); });
  despues(3000, () => { poner("¡SUELDA!", true); sonido.suelda(); });
}

// --- ronda -------------------------------------------------------------------------------------------------------
function xFantasma(t) {
  // Posición del fantasma a los t s de empezar la carrera, con las velocidades de sus tramos.
  const f = st.fantasma;
  if (!f?.tramos?.length) return Math.min(C.LONGITUD_CORDON, t * 5);
  let x = 0, resto = t;
  for (const tr of f.tramos) {
    const v = Math.max(0.1, tr.velocidad || 5);
    const dur = C.TAMANO_TRAMO / v;
    if (resto <= dur) return x + resto * v;
    x += C.TAMANO_TRAMO;
    resto -= dur;
  }
  return C.LONGITUD_CORDON;
}
function alMuestra(m) {
  st.muestra = m;
  st.tMuestra = performance.now();
  if (st.pantalla !== "ronda") return;
  const suelda = m.gatillo && m.apoyada;
  if (suelda && st.carrera.t0 == null) st.carrera.t0 = performance.now();
  gemelo.punta(m);
  tiraRonda.juez(Math.max(0, Math.min(C.LONGITUD_CORDON, m.x)));
  const i = Math.floor(m.x / C.TAMANO_TRAMO);
  if (suelda && i >= 0 && i < C.N_TRAMOS && m.calidad !== "suelto") {
    const previa = st.tramos[i];
    if (previa == null || PEOR[m.calidad] > PEOR[previa]) {
      st.tramos[i] = m.calidad;
      gemelo.pintar(i, m.calidad);
      tiraRonda.pintar(i, m.calidad);
    }
  }
  // tramo caliente bajo la punta
  for (let k = 0; k < C.N_TRAMOS; k++) tiraRonda.caliente(k, suelda && k === i && st.tramos[k] === "bien");
  // aviso de apoyo: gatillo pulsado con la punta en el aire más de 0,25 s
  if (m.gatillo && !m.apoyada) {
    st.sinApoyoDesde ??= performance.now();
    if (performance.now() - st.sinApoyoDesde > 250 && $("#aviso-apoyo").hidden) { $("#aviso-apoyo").hidden = false; sonido.aviso(); }
  } else {
    st.sinApoyoDesde = null;
    $("#aviso-apoyo").hidden = true;
  }
  sonido.arco(suelda && m.calidad !== "suelto", m.calidad);
}
let animTotal = null;
function contarTotal(hasta) {
  const el = $("#hud-total");
  const desde = st.totalMostrado;
  const t0 = performance.now();
  cancelAnimationFrame(animTotal);
  const paso = (ahora) => {
    const k = reducido() ? 1 : Math.min(1, (ahora - t0) / 260);
    st.totalMostrado = desde + (hasta - desde) * (1 - (1 - k) ** 3);
    el.textContent = fmt(st.totalMostrado);
    if (k < 1) animTotal = requestAnimationFrame(paso);
  };
  animTotal = requestAnimationFrame(paso);
}
function pintarPuntos(p) {
  contarTotal(p.total ?? 0);
  const multi = $("#hud-multi");
  const antes = st.puntos;
  $("#hud-combo").textContent = `COMBO ${p.combo ?? 0}`;
  multi.textContent = `×${p.multiplicador ?? 1}`;
  multi.classList.toggle("x1", (p.multiplicador ?? 1) <= 1);
  if ((p.multiplicador ?? 1) !== (antes.multiplicador ?? 1)) {
    multi.classList.remove("pulso");
    void multi.offsetWidth;
    multi.classList.add("pulso");
  }
  st.puntos = { ...p };
}
function alPuntos(p) {
  const subio = p.total > st.puntos.total;
  pintarPuntos(p);
  if (subio) sonido.puntos();
  const ev = p.evento;
  if (ev) {
    if (ev.tipo === "malo" && /QUEMADO/.test(ev.texto)) { sello(ev.texto, "malo"); sonido.quemado(); golpe(true); }
    else if (ev.tipo === "malo" && /APOYA/.test(ev.texto)) sonido.error(); // ya lo dice el aviso grande
    else if (ev.tipo === "malo") { sello(ev.texto, "malo"); sonido.error(); }
    else if (ev.tipo === "epico") { sello(ev.texto, "epico", { y: 270 }); sonido.epico(); golpe(false); }
    else { sello(ev.texto, "bueno"); sonido.combo(p.combo); }
  }
}
function alFantasmaVivo(f) {
  const q = $("#carrera-quien");
  const juez = f.va_ganando === "juez";
  q.textContent = juez ? "¡TÚ!" : st.personaje.nombre.toUpperCase();
  q.className = `carrera-quien ${juez ? "juez" : "robot"}`;
  const mm = Math.abs(f.ventaja_mm ?? 0), s = Math.abs(f.ventaja_s ?? 0);
  $("#carrera-dif").textContent = `+${mm.toFixed(0)} mm · ${s.toFixed(1).replace(".", ",")} s`;
}

// --- resultado ---------------------------------------------------------------------------------------------------
const FILAS_METRICAS = [
  ["cobertura", "Cobertura", (v) => `${Math.round(v * 100)} %`, "≥ 90 %", (v) => v >= 0.9],
  ["ritmo", "Ritmo", (v) => `${Math.round(v * 100)} %`, "≥ 70 %", (v) => v >= 0.7],
  ["quemados", "Quemados", (v) => `${v}`, "0", (v) => v === 0],
  ["desvio", "Desvío", (v) => `${v.toFixed(1).replace(".", ",")} mm`, "≤ 5 mm", (v) => v <= 5],
  ["angulo", "Ángulo", (v) => `${v.toFixed(0)}°`, "45° ± 15°", (v) => Math.abs(v - 45) <= 15],
  ["apoyo", "Apoyo", (v) => `${Math.round(v * 100)} %`, "≥ 90 %", (v) => v >= 0.9],
];
function pintarResultado(r) {
  st.resultado = r;
  if (st.pantalla !== "resultado") irA("resultado");
  const total = $("#res-total");
  const fin = r.puntos ?? 0;
  const t0 = performance.now(), dur = reducido() ? 1 : 1600;
  let ultimoTic = 0;
  const contar = (ahora) => {
    const k = Math.min(1, (ahora - t0) / dur);
    const e = 1 - (1 - k) ** 3;
    total.textContent = fmt(fin * e);
    if (ahora - ultimoTic > 70 && k < 1) { sonido.puntos(); ultimoTic = ahora; }
    if (k < 1 && st.pantalla === "resultado") requestAnimationFrame(contar);
  };
  requestAnimationFrame(contar);
  $("#res-nota").textContent = r.nota != null ? String(r.nota.toFixed ? r.nota.toFixed(1) : r.nota).replace(".", ",") : "–";
  const met = r.metricas || {};
  $("#res-metricas tbody").innerHTML = FILAS_METRICAS.filter(([k]) => met[k] != null).map(([k, nombre, f, tol, ok]) => {
    const v = met[k];
    const obj = typeof v === "object" ? v : null;
    const texto = obj ? obj.texto : f(v);
    const bien = obj ? obj.ok : ok(v);
    return `<tr><td>${nombre}</td><td>${escapar(texto)}</td><td>${obj?.tolerancia ?? tol}</td>` +
      `<td class="marca ${bien ? "ok" : "mal"}">${bien ? "✓" : "✕"}</td></tr>`;
  }).join("");
  const tramos = r.tramos || st.tramos;
  tiraRes.todo(tramos);
  gemelo.pintarTodo(tramos.map((c) => c || null));
  const ver = $("#res-veredicto");
  ver.innerHTML = "";
  const tampon = (texto, clase, sub) => {
    const d = document.createElement("div");
    d.className = `tampon ${clase} golpe`;
    d.innerHTML = `${texto}${sub ? `<small>${sub}</small>` : ""}`;
    ver.append(d);
    sonido.sello();
    return d;
  };
  despues(1700, () => {
    if (r.gana_al_robot) { tampon("HAS GANADO<br>AL ROBOT", "verde", "visto bueno del taller"); sonido.epico(); }
    else { tampon("GANA<br>EL ROBOT", "rojo", "revisar y repetir"); sonido.risa(); }
  });
  if (r.record) despues(2600, () => { const d = tampon("¡NUEVO RÉCORD!", "arco"); d.style.rotate = "5deg"; d.style.marginTop = "24px"; sonido.fanfarria(); });
  $("#insignia").hidden = true;
  if (r.insignia) despues(r.record ? 3600 : 2600, () => pintarInsignia(r.insignia));
}
function pintarInsignia(ins) {
  const nombre = typeof ins === "string" ? ins : ins.nombre || ins.titulo || "insignia";
  const el = $("#insignia");
  const texto = `${nombre.toUpperCase()} · LEWELDER · ${fechaHoy()} · `;
  el.innerHTML = `<svg viewBox="-110 -110 220 220" class="tampon-svg">
    <defs><path id="circ" d="M0,-80 a80,80 0 1,1 -0.1,0"/></defs>
    <circle r="100" fill="none" stroke="#ffc56b" stroke-width="5"/>
    <circle r="66" fill="none" stroke="#ffc56b" stroke-width="2"/>
    <text font-family="Share Tech Mono" font-size="17" fill="#ffc56b" letter-spacing="1.5"><textPath href="#circ">${escapar(texto)}</textPath></text>
    <path d="M-34 22H34M-14 22V-30l28 0" fill="none" stroke="#ffc56b" stroke-width="4"/>
    <path d="M-14 22l-18 0 18-18z" fill="#ff8a1f" stroke="#ff8a1f" stroke-width="2" stroke-linejoin="round"/>
  </svg>`;
  el.hidden = false;
  el.classList.remove("tampon");
  el.style.rotate = "-10deg";
  sonido.sello();
}

// --- iniciales ---------------------------------------------------------------------------------------------------
function pintarLetras() {
  document.querySelectorAll(".letra").forEach((el, i) => {
    el.querySelector("output").textContent = st.iniciales[i];
    el.classList.toggle("activa", i === st.letraActiva);
  });
  $("#cj-juez").textContent = st.iniciales.join("");
}
function moverLetra(i, paso) {
  const k = LETRAS.indexOf(st.iniciales[i]);
  st.iniciales[i] = LETRAS[(k + paso + LETRAS.length) % LETRAS.length];
  st.letraActiva = i;
  sonido.toque();
  pintarLetras();
}
document.querySelectorAll(".letra").forEach((el, i) => {
  el.querySelector(".arriba").addEventListener("click", () => moverLetra(i, -1));
  el.querySelector(".abajo").addEventListener("click", () => moverLetra(i, 1));
  el.querySelector("output").addEventListener("click", () => { st.letraActiva = i; pintarLetras(); });
});
function firmar() {
  sonido.sello();
  enviar({ orden: "iniciales", texto: st.iniciales.join("") });
}
$("#b-firmar").addEventListener("click", firmar);
window.addEventListener("keydown", (ev) => {
  if (st.pantalla !== "iniciales") return;
  const t = ev.key.toUpperCase();
  if (LETRAS.includes(t) && t.length === 1) {
    st.iniciales[st.letraActiva] = t;
    st.letraActiva = Math.min(2, st.letraActiva + 1);
    pintarLetras();
  } else if (ev.key === "ArrowUp") moverLetra(st.letraActiva, -1);
  else if (ev.key === "ArrowDown") moverLetra(st.letraActiva, 1);
  else if (ev.key === "ArrowLeft") { st.letraActiva = Math.max(0, st.letraActiva - 1); pintarLetras(); }
  else if (ev.key === "ArrowRight") { st.letraActiva = Math.min(2, st.letraActiva + 1); pintarLetras(); }
  else if (ev.key === "Enter") firmar();
});

// --- ranking -----------------------------------------------------------------------------------------------------
function pintarRanking() {
  $("#bom-ranking").innerHTML = htmlBom(st.ranking.top || [], { nueva: st.ranking.posicion_nueva ?? null });
  if (st.pantalla === "atraccion") pintarBomAtraccion();
}

// --- botones generales -------------------------------------------------------------------------------------------
lamina.addEventListener("pointerdown", (ev) => {
  sonido.despertar();
  if (st.pantalla === "atraccion" && !ev.target.closest(".controles")) {
    sonido.toque();
    enviar({ orden: "jugar" });
  }
}, { capture: true });
$("#b-montoyo").addEventListener("click", () => { sonido.toque(); enviar({ orden: "monto_yo" }); });
$("#b-otra").addEventListener("click", () => { sonido.toque(); enviar({ orden: "jugar" }); });
const bSonido = $("#b-sonido");
function pintarSonido() {
  bSonido.setAttribute("aria-pressed", String(sonido.silencio));
  bSonido.setAttribute("aria-label", sonido.silencio ? "Activar el sonido" : "Silenciar");
}
bSonido.addEventListener("click", () => {
  sonido.silencio = !sonido.silencio;
  pintarSonido();
  if (!sonido.silencio) sonido.toque();
});
pintarSonido();
$("#cj-fecha").textContent = fechaHoy();

// --- bucle de la app (cosas que siguen al 3D o al reloj) ---------------------------------------------------------
function bucle() {
  if (st.pantalla === "ronda") {
    if (st.carrera.t0 != null) {
      const x = xFantasma((performance.now() - st.carrera.t0) / 1000);
      st.carrera.x = x;
      gemelo.fantasma(x);
      tiraRonda.robot(x);
    }
    if (performance.now() - st.tMuestra > 400) sonido.arco(false);
  }
  lineaReferencia();
  requestAnimationFrame(bucle);
}
requestAnimationFrame(bucle);

// --- mensajes del servidor ---------------------------------------------------------------------------------------
export function recibir(msg) {
  switch (msg.tipo) {
    case "pantalla": irA(msg.nombre); break;
    case "personaje": hablar(msg); break;
    case "orden_propuesta": proponer(msg); break;
    case "robot":
      if (st.pantalla === "montaje") {
        pintarFases(msg.fase, msg.progreso ?? 0);
        gemelo.montaje(msg.progreso ?? 0);
        if (msg.imagen_jpeg_base64) {
          $("#detalle").hidden = false;
          $("#detalle-img").src = `data:image/jpeg;base64,${msg.imagen_jpeg_base64}`;
        }
      } else if (st.pantalla === "demostracion") {
        pintarDemo(msg.progreso ?? 0);
      }
      break;
    case "junta":
      st.junta = msg;
      pintarJunta(msg);
      if (st.pantalla === "reconocer") sonido.sello();
      break;
    case "alcance": pintarAlcance(msg); break;
    case "fantasma": st.fantasma = msg; break;
    case "muestra": alMuestra(msg); break;
    case "puntos":
      if (st.pantalla === "iniciales") $("#ini-puntos").textContent = fmt(msg.total ?? 0);
      else alPuntos(msg);
      break;
    case "fantasma_vivo": alFantasmaVivo(msg); break;
    case "resultado": pintarResultado(msg); break;
    case "ranking": st.ranking = msg; pintarRanking(); break;
    default: break;
  }
}

export function conectar(t) {
  transporte = t;
  $("#b-saltar").hidden = !t.saltar;
  $("#b-saltar").onclick = () => { sonido.toque(); t.saltar?.(); };
}
export function conexion(ok) {
  $("#conexion").hidden = ok;
}

// Para pruebas y capturas.
window.lewelder = { st, recibir, irA, gemelo, sonido };

// --- arranque ----------------------------------------------------------------------------------------------------
const params = new URLSearchParams(location.search);
await document.fonts.ready;
if (params.has("maqueta")) {
  const { arrancarMaqueta } = await import("./maqueta.js");
  arrancarMaqueta({ recibir, conectar, inicio: params.get("pantalla") });
} else {
  const { arrancarCliente } = await import("./cliente.js");
  arrancarCliente({ recibir, conectar, conexion });
}
