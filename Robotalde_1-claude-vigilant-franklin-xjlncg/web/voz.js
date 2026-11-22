// LeWelder · componente de voz (aislado). Micrófono → POST /api/voz → tarjeta "¿Monto…?" con Sí / No, y la voz
// del personaje (Chispas) con speechSynthesis. Sin dependencias; estilos en voz.css (clases vz-*).
//
//   import { crearComponenteVoz } from "./voz.js";
//   const voz = crearComponenteVoz(document.getElementById("caja-voz"), {
//     contexto: () => ({ junta_montada: "t" }),          // opcional: lo que la tablet sabe del taller
//     alConfirmar: (interp) => enviar({ orden: "robot", instruccion: interp.orden }),
//     alCancelar: (interp) => {},
//   });
//   voz.decir("¡Esquina servida!");                    // el personaje habla (bocadillo + voz)
//
// Reconocimiento con la Web Speech API (webkitSpeechRecognition, es-ES) si el navegador la tiene; si no, o si
// falla (sin permiso, sin red), el campo de texto de respaldo hace lo mismo.

const PERSONAJE_POR_DEFECTO = { nombre: "Chispas", voz: { lang: "es-ES", rate: 1.12, pitch: 1.35 } };

const ROBOT_SVG = `
<svg viewBox="0 0 64 64" aria-hidden="true">
  <defs>
    <linearGradient id="vz-casco" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffb066"/><stop offset="1" stop-color="#e8630c"/>
    </linearGradient>
  </defs>
  <path d="M32 3v7" stroke="#ffd27a" stroke-width="3" stroke-linecap="round"/>
  <circle cx="32" cy="3.5" r="3.2" fill="#ffe27a"/>
  <rect x="9" y="11" width="46" height="40" rx="12" fill="url(#vz-casco)"/>
  <rect x="14" y="20" width="36" height="17" rx="7" fill="#0b0e13"/>
  <circle class="vz-ojo" cx="24" cy="28.5" r="4.2" fill="#38bdf8"/>
  <circle class="vz-ojo" cx="40" cy="28.5" r="4.2" fill="#38bdf8"/>
  <rect class="vz-boca" x="23" y="42" width="18" height="3.6" rx="1.8" fill="#1b0d02"/>
  <rect x="3" y="24" width="6" height="14" rx="3" fill="#cf5a0b"/>
  <rect x="55" y="24" width="6" height="14" rx="3" fill="#cf5a0b"/>
</svg>`;

const MICRO_SVG = `
<svg viewBox="0 0 24 24" aria-hidden="true">
  <rect x="8.5" y="2.5" width="7" height="12" rx="3.5" fill="currentColor"/>
  <path d="M5 11a7 7 0 0 0 14 0M12 18v3.5M8.5 21.5h7" fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round"/>
</svg>`;

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

/** Habla con la voz del personaje (si el navegador sabe). Devuelve true si ha empezado a hablar. */
export function hablarComoPersonaje(texto, voz = PERSONAJE_POR_DEFECTO.voz, alTerminar = null) {
  if (!texto || !("speechSynthesis" in window)) return false;
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = voz.lang || "es-ES";
    const voces = speechSynthesis.getVoices();
    const elegida = voces.find((v) => v.lang === u.lang) || voces.find((v) => v.lang?.startsWith("es"));
    if (elegida) u.voice = elegida;
    u.rate = voz.rate ?? 1.12;
    u.pitch = voz.pitch ?? 1.35;
    if (alTerminar) { u.onend = alTerminar; u.onerror = alTerminar; }
    speechSynthesis.speak(u);
    return true;
  } catch (e) {
    return false;  // sin voz: el texto ya está en el bocadillo
  }
}

export function crearComponenteVoz(contenedor, opciones = {}) {
  const op = {
    endpoint: "api/voz",
    contexto: null,          // objeto o función que lo devuelve
    alConfirmar: () => {},
    alCancelar: () => {},
    hablar: true,            // speechSynthesis del personaje
    reconocimiento: true,    // false para forzar el campo de texto
    ...opciones,
  };
  let personaje = { ...PERSONAJE_POR_DEFECTO };
  let actual = null;         // última interpretación mostrada
  let escuchando = false;
  let reconocedor = null;
  let pidiendo = 0;          // id de la última petición (descarta respuestas viejas)

  // --- DOM ----------------------------------------------------------------------------------------------------
  const raiz = crear("section", "vz");
  raiz.setAttribute("aria-label", "Hablar con el robot");

  const robot = crear("div", "vz-robot");
  const avatar = crear("div", "vz-avatar");
  avatar.innerHTML = ROBOT_SVG;
  const bocadillo = crear("div", "vz-bocadillo");
  const nombre = crear("div", "vz-nombre", personaje.nombre);
  const dice = crear("p", "vz-dice", "Pídeme una junta: «móntame una esquina».");
  dice.setAttribute("aria-live", "polite");
  bocadillo.append(nombre, dice);
  robot.append(avatar, bocadillo);

  const centro = crear("div", "vz-centro");
  const micro = crear("button", "vz-micro");
  micro.type = "button";
  micro.innerHTML = `<span class="vz-onda"></span><span class="vz-onda vz-onda-2"></span>${MICRO_SVG}`;
  micro.setAttribute("aria-label", "Pulsa y habla");
  const estado = crear("div", "vz-estado", "Pulsa y habla");
  const oido = crear("div", "vz-oido");
  oido.hidden = true;
  centro.append(micro, estado, oido);

  const teclado = crear("form", "vz-teclado");
  const entrada = crear("input", "vz-entrada");
  entrada.type = "text";
  entrada.placeholder = "…o escribe la orden";
  entrada.setAttribute("aria-label", "Orden escrita");
  entrada.autocomplete = "off";
  entrada.maxLength = 300;
  const enviarBtn = crear("button", "vz-enviar", "Enviar");
  enviarBtn.type = "submit";
  teclado.append(entrada, enviarBtn);

  // tarjeta de confirmación (encima de todo el componente)
  const tarjeta = crear("div", "vz-tarjeta");
  tarjeta.hidden = true;
  tarjeta.setAttribute("role", "dialog");
  tarjeta.setAttribute("aria-modal", "false");
  const tEtiqueta = crear("div", "vz-tarjeta-etiqueta", "Confirma la orden");
  const tPregunta = crear("div", "vz-pregunta");
  const tOrden = crear("div", "vz-orden");
  const tBotones = crear("div", "vz-botones");
  const si = crear("button", "vz-si", "Sí");
  const no = crear("button", "vz-no", "No");
  si.type = no.type = "button";
  tBotones.append(si, no);
  const tOpciones = crear("div", "vz-opciones");
  tarjeta.append(tEtiqueta, tPregunta, tOrden, tBotones, tOpciones);

  raiz.append(robot, centro, teclado, tarjeta);
  contenedor.append(raiz);

  // --- personaje -----------------------------------------------------------------------------------------------
  function decir(texto, { hablar = op.hablar } = {}) {
    if (!texto) return;
    dice.textContent = texto;
    bocadillo.classList.remove("vz-pop");
    void bocadillo.offsetWidth;  // reinicia la animación
    bocadillo.classList.add("vz-pop");
    if (hablar && hablarComoPersonaje(texto, personaje.voz, () => raiz.classList.remove("vz-hablando"))) {
      raiz.classList.add("vz-hablando");
    }
  }

  function ponerEstado(texto, clase = "") {
    estado.textContent = texto;
    estado.className = `vz-estado ${clase}`.trim();
  }

  // --- tarjeta -------------------------------------------------------------------------------------------------
  function ocultar() {
    tarjeta.hidden = true;
    raiz.classList.remove("vz-con-tarjeta");
  }

  function mostrarConfirmacion(orden, pregunta) {
    tarjeta.dataset.tipo = "confirmar";
    tEtiqueta.textContent = "Confirma la orden";
    tPregunta.textContent = pregunta;
    tOrden.textContent = `«${orden}»`;
    tOrden.hidden = false;
    tBotones.hidden = false;
    tOpciones.hidden = true;
    tarjeta.hidden = false;
    raiz.classList.add("vz-con-tarjeta");
    si.focus({ preventScroll: true });
  }

  function mostrarOpciones(interp) {
    tarjeta.dataset.tipo = "aclarar";
    tEtiqueta.textContent = "¿Cuál quieres?";
    tPregunta.textContent = interp.aclaracion;
    tOrden.hidden = true;
    tBotones.hidden = true;
    tOpciones.replaceChildren(...interp.botones.map((b) => {
      const btn = crear("button", "vz-opcion", b.etiqueta);
      btn.type = "button";
      btn.onclick = () => {
        actual = { ...interp, orden: b.orden, pregunta: b.pregunta, aclaracion: null, confirmable: true };
        mostrarConfirmacion(b.orden, b.pregunta);
      };
      return btn;
    }));
    const cancelar = crear("button", "vz-opcion vz-opcion-no", "Nada");
    cancelar.type = "button";
    cancelar.onclick = () => responder(false);
    tOpciones.append(cancelar);
    tOpciones.hidden = false;
    tarjeta.hidden = false;
    raiz.classList.add("vz-con-tarjeta");
  }

  /** Enseña una interpretación de /api/voz (tarjeta, aclaración o respuesta del personaje). */
  function mostrar(interp) {
    actual = interp;
    if (interp.personaje) personaje = interp.personaje;
    nombre.textContent = personaje.nombre;
    decir(interp.respuesta);
    if (interp.confirmable) {
      ponerEstado("¿Lo confirmas?", "vz-ok");
      mostrarConfirmacion(interp.orden, interp.pregunta);
    } else if (interp.aclaracion && interp.botones?.length) {
      ponerEstado(interp.aclaracion, "vz-duda");
      mostrarOpciones(interp);
    } else {
      ocultar();
      ponerEstado(interp.orden ? "Ahora no se puede" : "No te he entendido", "vz-mal");
    }
  }

  function responder(siONo) {
    const interp = actual;
    ocultar();
    if (!interp) return;
    if (siONo && interp.orden) {
      ponerEstado(`Orden enviada: ${interp.orden}`, "vz-ok");
      op.alConfirmar(interp);
    } else {
      ponerEstado("Pulsa y habla");
      decir("Vale, no hago nada, tú mandas.");
      op.alCancelar(interp);
    }
    actual = null;
  }
  si.onclick = () => responder(true);
  no.onclick = () => responder(false);

  // --- servidor ------------------------------------------------------------------------------------------------
  async function enviarTexto(texto, alternativas = []) {
    texto = (texto || "").trim();
    if (!texto) return null;
    const id = ++pidiendo;
    oido.hidden = false;
    oido.textContent = `«${texto}»`;
    ponerEstado("Pensando…", "vz-pensando");
    raiz.classList.add("vz-ocupado");
    const contexto = typeof op.contexto === "function" ? op.contexto() : op.contexto;
    try {
      const r = await fetch(op.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto, alternativas, ...(contexto ? { contexto } : {}) }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const interp = await r.json();
      if (id === pidiendo) mostrar(interp);
      return interp;
    } catch (e) {
      if (id === pidiendo) ponerEstado("Sin conexión con el servidor", "vz-mal");
      return null;
    } finally {
      if (id === pidiendo) raiz.classList.remove("vz-ocupado");
    }
  }

  teclado.onsubmit = (ev) => {
    ev.preventDefault();
    const texto = entrada.value;
    entrada.value = "";
    entrada.blur();
    enviarTexto(texto);
  };

  // --- reconocimiento de voz -----------------------------------------------------------------------------------
  const SR = op.reconocimiento ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;

  function sinMicrofono(motivo) {
    raiz.classList.add("vz-sin-micro");
    micro.setAttribute("aria-label", "Escribe la orden");
    ponerEstado(motivo, "vz-mal");
  }

  function parar() {
    escuchando = false;
    raiz.classList.remove("vz-escuchando");
    try { reconocedor?.stop(); } catch (e) { /* ya parado */ }
  }

  function escuchar() {
    if (!SR) { entrada.focus(); return; }
    if (escuchando) { parar(); return; }
    if ("speechSynthesis" in window) speechSynthesis.cancel();  // que el robot no se oiga a sí mismo
    ocultar();
    reconocedor = new SR();
    reconocedor.lang = "es-ES";
    reconocedor.interimResults = true;
    reconocedor.maxAlternatives = 3;
    reconocedor.continuous = false;
    reconocedor.onresult = (ev) => {
      const res = ev.results[ev.results.length - 1];
      oido.hidden = false;
      oido.textContent = `«${res[0].transcript}»`;
      if (res.isFinal) {
        const alternativas = Array.from(res).slice(1).map((a) => a.transcript);
        parar();
        enviarTexto(res[0].transcript, alternativas);
      }
    };
    reconocedor.onerror = (ev) => {
      parar();
      if (ev.error === "not-allowed" || ev.error === "service-not-allowed") sinMicrofono("Sin permiso de micrófono: escribe la orden");
      else if (ev.error === "network") sinMicrofono("Sin reconocimiento de voz: escribe la orden");
      else if (ev.error === "no-speech") ponerEstado("No he oído nada, prueba otra vez");
      else ponerEstado("No te he oído bien, prueba otra vez");
    };
    reconocedor.onend = () => { if (escuchando) parar(); };
    try {
      reconocedor.start();
      escuchando = true;
      raiz.classList.add("vz-escuchando");
      ponerEstado("Te escucho…", "vz-escucha");
      oido.hidden = true;
    } catch (e) {
      sinMicrofono("Micrófono no disponible: escribe la orden");
    }
  }
  micro.onclick = escuchar;
  if (!SR) sinMicrofono("Este navegador no reconoce voz: escribe la orden");

  return {
    raiz,
    escuchar,
    enviarTexto,
    mostrar,
    ocultar,
    decir,
    get personaje() { return personaje; },
    destruir() { parar(); raiz.remove(); },
  };
}
