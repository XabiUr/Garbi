// Garbi · app del producto. JavaScript sin dependencias: funciona sin internet.
"use strict";

const ESTADOS = {
  apagado:          { titulo: "Apagado",             icono: '<path d="M12 3v8M6.3 7.3a8 8 0 1 0 11.4 0"/>' },
  arrancando:       { titulo: "Arrancando…",         icono: '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/>' },
  reposo:           { titulo: "En reposo",           icono: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>' },
  acercamiento:     { titulo: "Acercándose",         icono: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>' },
  en_broca:         { titulo: "En la broca",         icono: '<path d="M12 2v6M9 8h6l-1 10-2 4-2-4-1-10Z"/><path d="M4 18c2-1 3-3 3-5M20 18c-2-1-3-3-3-5"/>' },
  despierto:        { titulo: "Despierto",           icono: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>' },
  limpieza_tabla:   { titulo: "Limpiando la tabla",  icono: '<rect x="3" y="7" width="18" height="10" rx="1.5"/><path d="M6 10h12M6 14h8"/>' },
  limpieza_tapete:  { titulo: "Limpiando el tapete", icono: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 14h18M9 4v16M15 4v16"/>' },
  emergencia:       { titulo: "EMERGENCIA",          icono: '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4M12 17v.5"/>' },
};

// Modo «Fábrica»: los mismos estados con nombres de planta.
const TITULOS_FABRICA = {
  apagado: "Equipo apagado", arrancando: "Arranque en curso", reposo: "Reposo · listo", acercamiento: "Aproximación", en_broca: "En posición · aspirando",
  despierto: "Espera entre ciclos", limpieza_tabla: "Ciclo limpieza tabla", limpieza_tapete: "Ciclo limpieza tapete",
  emergencia: "Paro de emergencia",
};

const ICONOS_TEC = {
  vision:     '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3" fill="currentColor"/>',
  manos:      '<path d="M7 11V5a1.5 1.5 0 0 1 3 0v5M10 10V3.5a1.5 1.5 0 0 1 3 0V10M13 10V4.5a1.5 1.5 0 0 1 3 0V11M16 11V7.5a1.5 1.5 0 0 1 3 0V14a7 7 0 0 1-7 7h-.5A6.5 6.5 0 0 1 6 17.5L3.5 13a1.5 1.5 0 0 1 2.6-1.5L7 13"/>',
  politica:   '<path d="M12 4a3 3 0 0 0-3 3 3 3 0 0 0-3 3c0 1 .5 2 1.3 2.5A3 3 0 0 0 9 18a3 3 0 0 0 3 2V4ZM12 4a3 3 0 0 1 3 3 3 3 0 0 1 3 3c0 1-.5 2-1.3 2.5A3 3 0 0 1 15 18a3 3 0 0 1-3 2"/>',
  robot:      '<rect x="5" y="8" width="14" height="11" rx="2"/><path d="M12 4v4M9 13h.01M15 13h.01M9 16h6"/>',
  aspiradora: '<path d="M4 20h7l2-6H6a2 2 0 0 0-2 2v4ZM13 14l5-10M18 4h2"/>',
  llm:        '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/>',
  seta:       '<circle cx="12" cy="10" r="6"/><path d="M9 16v4h6v-4"/>',
};

const NOMBRES_TEC = {
  vision: ["Visión", "Círculo morado del taladro"],
  manos: ["Manos", "MediaPipe · mano + taladro"],
  politica: ["Política", ""],
  robot: ["Robot", "SO-101"],
  aspiradora: ["Aspiradora", "Arduino"],
  llm: ["Asistente", ""],
  seta: ["Seta", "Barra espaciadora"],
  circulo: ["Círculo morado", "Detector OpenCV"],
  tabla: ["Tabla", "Pieza sobre el tapete"],
  matriz: ["Matriz", "Píxel → postura"],
};
const ORDEN_TEC = ["vision", "circulo", "manos", "tabla", "politica", "matriz", "robot", "aspiradora", "llm", "seta"];

const $ = (sel) => document.querySelector(sel);
let ultimo = null;               // último estado recibido
let eventosVistos = new Set();
let aspirabaManual = false;
let temporizadorApagar = null;
let modo = "taller";             // "taller" o "fabrica"
const fabrica = () => modo === "fabrica";

// ------------------------------------------------------------------------------------------------- utilidades
function sinTildes(s) { return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); }

function nivel(valor) {
  // "ok", "ok: detalle", "aviso: ...", "error: ...", "manual"
  const v = (valor || "").trim();
  const m = v.match(/^(ok|aviso|error|manual)\s*:?\s*(.*)$/i);
  if (!m) return { nivel: "aviso", detalle: v };
  return { nivel: m[1].toLowerCase(), detalle: m[2] };
}

function esManual(e) { return nivel((e.tecnologias || {}).aspiradora).nivel === "manual"; }

async function post(url, datos) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                               body: JSON.stringify(datos || {}) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function pitido(frecuencia = 880, duracion = 0.18) {
  try {
    const ctx = pitido.ctx || (pitido.ctx = new (window.AudioContext || window.webkitAudioContext)());
    const osc = ctx.createOscillator(), gan = ctx.createGain();
    osc.frequency.value = frecuencia; osc.connect(gan); gan.connect(ctx.destination);
    gan.gain.setValueAtTime(0.15, ctx.currentTime);
    gan.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duracion);
    osc.start(); osc.stop(ctx.currentTime + duracion);
  } catch (_) { /* sin audio: no pasa nada */ }
}

// ------------------------------------------------------------------------------------------------- estado
function pintar(e) {
  const info = ESTADOS[e.estado] || { titulo: e.estado, icono: "" };
  const tarjeta = $("#tarjeta-estado");
  tarjeta.dataset.estado = e.estado;
  tarjeta.style.setProperty("--color-estado", `var(--e-${e.estado}, var(--e-reposo))`);
  $("#estado-titulo").textContent = fabrica() ? (TITULOS_FABRICA[e.estado] || info.titulo) : info.titulo;
  $("#estado-detalle").textContent = e.detalle || "";
  $("#estado-icono").innerHTML = `<svg viewBox="0 0 24 24">${info.icono}</svg>`;
  document.title = `Garbi · ${info.titulo}`;

  const manual = esManual(e);
  const dato = $("#dato-aspiradora");
  dato.classList.toggle("activo", e.aspiradora && !manual);
  dato.classList.toggle("manual", manual);
  $("#valor-aspiradora").textContent = manual
    ? (e.aspiradora ? (fabrica() ? "Activar pedal" : "¡Enciéndela!") : (fabrica() ? "Manual · OFF" : "Manual · apagada"))
    : (e.aspiradora ? (fabrica() ? "ON" : "Aspirando") : (fabrica() ? "OFF" : "Apagada"));
  $("#valor-agujeros").textContent = e.agujeros ?? 0;
  $("#valor-politica").textContent = e.politica === "act" ? "ACT" : (e.politica === "circulo" ? "Círculo"
    : (e.politica === "zonas" ? "Zonas" : e.politica));
  document.querySelectorAll("[data-cerebro]").forEach((b) => b.classList.toggle("activo", b.dataset.cerebro === e.politica));

  const emergencia = e.estado === "emergencia";
  document.body.classList.toggle("en-emergencia", emergencia);
  $("#aviso-emergencia").hidden = !emergencia;
  $("#boton-rearmar-lateral").hidden = !emergencia;   // rearmar solo tiene sentido en paro
  pintarControles(e);

  $("#chip-demo").hidden = !e.demo;
  const chipLlm = $("#chip-llm");
  chipLlm.textContent = e.llm === "claude" ? "Claude" : "Sin conexión";
  chipLlm.classList.toggle("claude", e.llm === "claude");

  // Toast de encender/apagar la aspiradora quitado (avisoAspiradora ya no se llama).
  pintarIndicadores(e.indicadores || {});
  pintarTecnologias(e);
  pintarEventos(e.eventos || []);
}

function avisoAspiradora(e, manual) {
  // Sin Arduino la aspiradora se enciende con el pie: aviso grande al empezar y al terminar.
  const aviso = $("#aviso-aspiradora");
  const quiere = manual && e.aspiradora && e.estado !== "emergencia";
  if (quiere) {
    clearTimeout(temporizadorApagar); temporizadorApagar = null;
    aviso.className = "aviso-aspiradora encender";
    $("#aviso-aspiradora-titulo").textContent = fabrica() ? "ACTIVAR ASPIRACIÓN (PEDAL)"
                                                           : "¡Enciende la aspiradora con el pie!";
    $("#aviso-aspiradora-texto").textContent = fabrica()
      ? "Aspiración manual: el ciclo requiere aspiración ahora."
      : (e.estado === "en_broca" ? "Garbi ha llegado a la broca y quiere aspirar."
                                 : "Garbi está barriendo y necesita la aspiradora.");
    aviso.hidden = false;
    if (!aspirabaManual) { pitido(880); setTimeout(() => pitido(1175), 200); }
  } else if (aspirabaManual && manual) {
    aviso.className = "aviso-aspiradora apagar";
    $("#aviso-aspiradora-titulo").textContent = fabrica() ? "Desactivar aspiración (pedal)"
                                                           : "Ya puedes apagar la aspiradora";
    $("#aviso-aspiradora-texto").textContent = fabrica() ? "Fin de la fase de aspiración."
                                                          : "Garbi ha terminado de aspirar.";
    aviso.hidden = false;
    pitido(660);
    temporizadorApagar = setTimeout(() => { aviso.hidden = true; }, 4000);
  } else if (!manual) {
    aviso.hidden = true;
  }
  aspirabaManual = quiere;
}

function duracion(s) {
  s = Math.round(s || 0);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), seg = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(seg).padStart(2, "0")}` : `${m}:${String(seg).padStart(2, "0")}`;
}

// Controles: la acción principal cambia con el estado; lo que no se puede usar se desactiva y se dice por qué.
let limpiezaPedida = 0;   // instante en que se pulsó una limpieza: bloquea las demás hasta que cambie el estado
function pintarControles(e) {
  const est = e.estado, det = e.detalle || "";
  const apagado = est === "apagado", arrancando = est === "arrancando", apagando = det.startsWith("Apagando");
  const emergencia = est === "emergencia";
  const limpiando = est === "limpieza_tabla" || est === "limpieza_tapete";
  // Listo = en reposo de verdad y sin una limpieza recién pedida (hasta que el estado cambie)
  if (limpiezaPedida && (est !== "reposo" || Date.now() - limpiezaPedida > 5000)) limpiezaPedida = 0;
  const listo = !apagando && est === "reposo" && !limpiezaPedida;

  // Equipo
  const be = $("#boton-energia");
  const esperando = arrancando || apagando;
  be.dataset.comando = apagado ? "encender" : "apagar";
  be.disabled = esperando;
  be.classList.toggle("esperando", esperando);
  be.classList.toggle("es-principal", apagado);
  be.classList.toggle("es-apagar", !apagado && !esperando);
  $("#texto-energia").textContent = arrancando ? "Arrancando…" : apagando ? "Apagando…"
    : apagado ? (fabrica() ? "Marcha" : "Encender") : (fabrica() ? "Paro" : "Apagar");
  $("#ayuda-equipo").textContent = apagado ? "El robot está apagado"
    : arrancando ? "Conectando el robot y yendo a reposo…" : apagando ? "Volviendo a reposo para apagarse…"
    : emergencia ? "En emergencia: rearma para seguir" : "Encendido";

  // Brazo
  const motivo = apagado ? "Enciende el equipo para usar el brazo"
    : arrancando ? "Espera a que termine de arrancar" : apagando ? "El equipo se está apagando"
    : emergencia ? "Rearma la emergencia antes de mover el brazo"
    : limpiando ? "Limpiando · pulsa Parar para detener"
    : limpiezaPedida ? "Limpieza pedida · empezando…"
    : listo ? "Listo · el brazo se moverá al pulsar" : "Disponible cuando el brazo vuelva a reposo";
  document.querySelectorAll(".controles .boton-accion").forEach((b) => {
    b.disabled = !listo;
    b.classList.toggle("es-principal", listo);
    b.title = listo ? "" : motivo;
  });
  const bp = $(".controles .boton-parar");
  bp.disabled = !limpiando;
  bp.classList.toggle("es-principal", limpiando);
  bp.title = limpiando ? "" : "No hay ninguna limpieza en marcha";
  $("#ayuda-brazo").textContent = motivo;

  // Configuración: solo en reposo (nunca a mitad de un movimiento)
  document.querySelectorAll("[data-cerebro]").forEach((b) => {
    b.disabled = !listo;
    b.title = listo ? "" : "Se puede cambiar con el brazo en reposo";
  });
}

function pintarIndicadores(ind) {
  const poner = (clave, texto) => { const el = document.getElementById(`kpi-${clave}`); if (el) el.textContent = texto; };
  poner("agujeros", ind.agujeros ?? 0);
  poner("t_aspirando", duracion(ind.t_aspirando));
  poner("limpiezas_tabla", ind.limpiezas_tabla ?? 0);
  poner("limpiezas_tapete", ind.limpiezas_tapete ?? 0);
  poner("t_emergencia", duracion(ind.t_emergencia));
  const disp = Math.max(0, Math.min(1, ind.disponibilidad ?? 1));
  poner("disponibilidad", `${(disp * 100).toFixed(disp >= 0.999 ? 0 : 1)} %`);
  $("#kpi-barra-disponibilidad").style.width = `${disp * 100}%`;
}

function pintarTecnologias(e) {
  if (!$("#lista-tecnologias")) return;   // tarjeta quitada de la página
  const tec = e.tecnologias || {};
  const claves = Object.keys(tec).map((k) => [sinTildes(k), k]);
  const orden = [...ORDEN_TEC.filter((k) => claves.some(([n]) => n === k)),
                 ...claves.map(([n]) => n).filter((n) => !ORDEN_TEC.includes(n))];
  const html = orden.map((n) => {
    const original = claves.find(([c]) => c === n)[1];
    const { nivel: niv, detalle } = nivel(tec[original]);
    let [nombre, sub] = NOMBRES_TEC[n] || [original, ""];
    if (n === "politica") sub = e.politica === "act" ? (fabrica() ? "ACT (aprendizaje por imitación)" : "ACT entrenado")
                                                     : "Círculo + matriz";
    if (n === "llm") sub = e.llm === "claude" ? "Claude" : (fabrica() ? "Local, sin red" : "Palabras clave, sin internet");
    if (n === "aspiradora" && niv === "manual") sub = fabrica() ? "Manual · pedal" : "Manual · con el pie";
    if (detalle) sub = sub ? `${sub} · ${detalle}` : detalle;
    const textoNivel = { ok: "OK", aviso: "Aviso", error: "Error", manual: "Manual" }[niv] || niv;
    // Estado con color Y texto (nunca solo color): el punto en el icono y la palabra en la segunda línea.
    return `<li class="tecnologia nivel-${niv}" title="${escapar(`${nombre} · ${textoNivel} · ${sub}`)}">
      <span class="tecnologia-icono"><svg viewBox="0 0 24 24">${ICONOS_TEC[n] || ICONOS_TEC.robot}</svg></span>
      <span class="tecnologia-texto"><span class="tecnologia-nombre">${escapar(nombre)}</span>
        <span class="tecnologia-sub"><b class="nivel">${textoNivel}</b>${sub ? " · " + escapar(sub) : ""}</span></span></li>`;
  }).join("");
  const lista = $("#lista-tecnologias");
  if (lista.dataset.html !== html) { lista.innerHTML = html; lista.dataset.html = html; }
}

function pintarEventos(eventos) {
  const lista = $("#lista-eventos");
  const html = eventos.slice(0, 30).map((ev) => {
    const [hora, ...resto] = ev.split(" · ");
    const texto = resto.length ? resto.join(" · ") : hora;
    const nuevo = !eventosVistos.has(ev) && eventosVistos.size > 0;
    return `<li class="${nuevo ? "nuevo" : ""}">${resto.length ? `<span class="hora">${escapar(hora)}</span>` : ""}<span>${escapar(texto)}</span></li>`;
  }).join("");
  if (lista.dataset.html !== html.replace(/ class="nuevo"/g, ' class=""')) {
    lista.innerHTML = html;
    lista.dataset.html = html.replace(/ class="nuevo"/g, ' class=""');
  }
  eventos.forEach((ev) => eventosVistos.add(ev));
}

function escapar(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function conexion(ok) {
  const chip = $("#chip-conexion");
  chip.hidden = ok;                       // solo se ve si se pierde la conexión
  chip.classList.toggle("desconectado", !ok);
  $("#texto-conexion").textContent = "Sin conexión con Garbi";
}

async function sondear() {
  try {
    const r = await fetch("/api/estado", { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    ultimo = await r.json();
    pintar(ultimo);
    conexion(true);
  } catch (_) {
    conexion(false);
  }
  setTimeout(sondear, 250);
}

// ------------------------------------------------------------------------------------------------- vídeo
function arrancarVideo(img) {
  const camara = img.dataset.camara;
  const cargar = () => { img.src = `/video/${camara}?t=${Date.now()}`; };
  img.addEventListener("error", () => setTimeout(cargar, 1000));
  cargar();
}

// ------------------------------------------------------------------------------------------------- confirmaciones
// Encender y Apagar mueven el brazo: siempre con confirmación. Al encender, comprobación manual (de momento) de que el
// camino está libre y el brazo en una posición normal.
function confirmarEnergia(comando, boton) {
  const modal = $(comando === "encender" ? "#modal-encender" : "#modal-apagar");
  if (comando === "encender") {
    const checks = [$("#check-camino"), $("#check-postura")];
    checks.forEach((c) => { c.checked = false; });
    const ok = $("#confirmar-encender");
    ok.disabled = true;
    checks.forEach((c) => { c.onchange = () => { ok.disabled = !checks.every((x) => x.checked); }; });
  }
  modal.returnValue = "";
  modal.onclose = () => { if (modal.returnValue === "confirmar") mandar(comando, boton); };
  modal.showModal();
}

// ------------------------------------------------------------------------------------------------- comandos
async function mandar(comando, boton) {
  try {
    await post("/api/comando", { comando });
    if (boton) { boton.classList.add("enviado"); setTimeout(() => boton.classList.remove("enviado"), 600); }
  } catch (err) {
    console.error(err);
  }
}

function emergencia(origen) {
  // Primero la orden (lo más rápido posible); luego la interfaz.
  fetch(`/api/emergencia?origen=${encodeURIComponent(origen)}`, { method: "POST", keepalive: true }).catch(() => {});
  const b = $("#boton-emergencia");
  b.classList.add("pulsado"); setTimeout(() => b.classList.remove("pulsado"), 200);
  document.body.classList.add("en-emergencia");
  $("#aviso-emergencia").hidden = false;
}

document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-comando]");
  if (b && b.id === "boton-energia") confirmarEnergia(b.dataset.comando, b);
  else if (b && b.classList.contains("boton-accion")) {
    // limpieza: bloquear al instante las dos (evita la doble pulsación antes de que llegue el nuevo estado)
    limpiezaPedida = Date.now();
    document.querySelectorAll(".controles .boton-accion").forEach((x) => { x.disabled = true; });
    mandar(b.dataset.comando, b);
  } else if (b) mandar(b.dataset.comando, b);
  const c = ev.target.closest("[data-cerebro]");
  if (c) fetch("/api/cerebro", {method: "POST", headers: {"Content-Type": "application/json"},
                                body: JSON.stringify({cerebro: c.dataset.cerebro})}).catch(() => {});
});
$("#boton-emergencia").addEventListener("click", () => emergencia("botón"));

// Seta USB = barra espaciadora. En cualquier sitio salvo escribiendo en el chat.
document.addEventListener("keydown", (ev) => {
  if (ev.code !== "Space" && ev.key !== " ") return;
  const t = ev.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
  ev.preventDefault();
  if (!ev.repeat) emergencia("espacio");
}, true);

// ------------------------------------------------------------------------------------------------- chat
const cajaMensajes = $("#chat-mensajes");
const entrada = $("#chat-texto");

function anadirMensaje(texto, quien, accion) {
  const div = document.createElement("div");
  div.className = `mensaje mensaje-${quien}`;
  div.textContent = texto;
  if (accion) {
    const s = document.createElement("span");
    s.className = "accion"; s.textContent = accion;
    div.appendChild(s);
  }
  cajaMensajes.appendChild(div);
  cajaMensajes.scrollTop = cajaMensajes.scrollHeight;
  return div;
}

const NOMBRES_COMANDO = { encender: "Encender", apagar: "Apagar", limpiar_tabla: "Limpiar tabla",
                          limpiar_tapete: "Limpiar tapete", parar: "Parar" };

async function enviarChat(texto) {
  texto = texto.trim();
  if (!texto) return;
  anadirMensaje(texto, "usuario");
  const pensando = anadirMensaje("Garbi está pensando…", "garbi");
  pensando.classList.add("escribiendo");
  try {
    const r = await post("/api/chat", { texto, modo });
    pensando.remove();
    const accion = (r.comandos || []).map((c) => `✓ ${NOMBRES_COMANDO[c] || c}`).join("  ");
    anadirMensaje(r.respuesta, "garbi", accion);
  } catch (_) {
    pensando.remove();
    anadirMensaje("No llego al servidor. ¿Está Garbi encendido?", "garbi");
  }
}

$("#chat-formulario").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const texto = entrada.value;
  entrada.value = "";
  enviarChat(texto);
});
$("#chat-sugerencias").addEventListener("click", (ev) => {
  if (ev.target.tagName === "BUTTON") enviarChat(ev.target.textContent);
});
// Mientras se escribe, la seta global (espacio fuera del navegador) no dispara.
entrada.addEventListener("focus", () => { $("#chat-nota").classList.add("visible"); post("/api/foco_chat", { foco: true }).catch(() => {}); });
entrada.addEventListener("blur", () => { $("#chat-nota").classList.remove("visible"); post("/api/foco_chat", { foco: false }).catch(() => {}); });
window.addEventListener("beforeunload", () => {
  navigator.sendBeacon?.("/api/foco_chat", new Blob([JSON.stringify({ foco: false })], { type: "application/json" }));
});

// Micrófono (Web Speech API) si el navegador lo tiene.
(function microfono() {
  const Reconocedor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Reconocedor) return;
  const boton = $("#boton-microfono");
  boton.hidden = false;
  const rec = new Reconocedor();
  rec.lang = "es-ES"; rec.interimResults = false; rec.maxAlternatives = 1;
  let escuchando = false;
  rec.onresult = (ev) => enviarChat(ev.results[0][0].transcript);
  rec.onend = () => { escuchando = false; boton.classList.remove("escuchando"); };
  rec.onerror = () => { escuchando = false; boton.classList.remove("escuchando"); };
  boton.addEventListener("click", () => {
    if (escuchando) { rec.stop(); return; }
    try { rec.start(); escuchando = true; boton.classList.add("escuchando"); } catch (_) { /* ya escuchando */ }
  });
})();

// ------------------------------------------------------------------------------------------------- modo
function aplicarModo(nuevo) {
  modo = nuevo === "fabrica" ? "fabrica" : "taller";
  document.body.classList.toggle("modo-fabrica", fabrica());
  document.querySelectorAll("[data-fabrica]").forEach((el) => {
    if (el.dataset.taller === undefined) el.dataset.taller = el.textContent;
    el.textContent = fabrica() ? el.dataset.fabrica : el.dataset.taller;
  });
  document.querySelectorAll(".selector-modo [data-modo]").forEach((b) => {
    b.setAttribute("aria-checked", String(b.dataset.modo === modo));
  });
  entrada.placeholder = fabrica() ? "Orden o consulta…" : "Escribe a Garbi…";
  try { localStorage.setItem("garbi.modo", modo); } catch (_) { /* sin almacenamiento */ }
  if (ultimo) pintar(ultimo);
}

// ------------------------------------------------------------------------------------------------- arranque
// El modo «Fábrica» se ha quitado: siempre «Taller» (y se olvida un modo guardado de antes)
try { localStorage.removeItem("garbi.modo"); } catch (_) { /* sin almacenamiento */ }
aplicarModo("taller");
document.querySelectorAll("img[data-camara]").forEach(arrancarVideo);
sondear();
