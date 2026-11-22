// Maqueta de LeWelder v2 (`index.html?maqueta=1`): un guion que hace de servidor. Emite los mensajes del protocolo
// v2 (PROTOCOLO.md) igual que lo hará la tarea 6b y recorre una ronda completa en ~90 s:
// atracción → pedir → montaje → reconocer → demostración → cuenta atrás → ronda (combos, un quemado, el juez despega
// la antorcha y adelanta al fantasma) → resultado → iniciales → ranking → atracción.
//
// - Avanza sola (para el vídeo y para enseñarla), pero responde a la tablet: "jugar", "confirmar", "iniciales",
//   "monto_yo" y "reiniciar" hacen lo mismo que harían con el servidor real.
// - Botón SALTAR: pasa a la escena siguiente. `&pantalla=ronda` (o cualquier otra) empieza en esa escena.
// - Simula también `/api/voz` (tarea 3): oye «¡Móntame una esquina!» y devuelve la interpretación.
// - Otras opciones para capturas: `&junta=t`, `&alcance=no`, `&gana=robot`, `&record=1`, `&incompleta=1`.
import * as C from "./contrato.js";

const PREGUNTAS = {
  "monta una unión en T": "¿Monto una unión en T?",
  "monta una unión en esquina": "¿Monto una unión en esquina?",
};
const PERSONAJE = { nombre: "Chispas", voz: { lang: "es-ES", rate: 1.12, pitch: 1.35 } };
const FICHAS = {
  esquina: {
    titulo: "Unión en esquina",
    para_que: "Cerrar cajas y bastidores: dos chapas que se tocan por el canto.",
    donde_se_usa: "Armarios eléctricos, depósitos, chasis y carrocería.",
    angulo: "45° entre las dos chapas · 0-20° de empuje · ritmo de 4-6 mm/s",
  },
  t: {
    titulo: "Unión en T",
    para_que: "Poner una chapa de pie sobre otra: refuerzos, nervios y soportes.",
    donde_se_usa: "Estructuras metálicas, barcos, vigas y escaleras.",
    angulo: "45° entre la base y el alma · 0-20° de empuje · ritmo de 4-6 mm/s",
  },
};
const TOP_BASE = [
  { iniciales: "IKR", puntos: 9120, junta: "esquina" },
  { iniciales: "MRT", puntos: 8450, junta: "t" },
  { iniciales: "UXU", puntos: 6980, junta: "esquina" },
  { iniciales: "LEO", puntos: 6210, junta: "t" },
  { iniciales: "AMA", puntos: 5540, junta: "esquina" },
  { iniciales: "JON", puntos: 4870, junta: "t" },
  { iniciales: "PEP", puntos: 4120, junta: "esquina" },
  { iniciales: "SO1", puntos: 3390, junta: "t" },
  { iniciales: "NEK", puntos: 2650, junta: "esquina" },
  { iniciales: "ZUR", puntos: 2080, junta: "t" },
];

class Saltar extends Error {}

export function arrancarMaqueta({ recibir, conectar, inicio }) {
  const params = new URLSearchParams(location.search);
  const op = {
    junta: params.get("junta") === "t" ? "t" : "esquina",
    alcance: params.get("alcance") !== "no",
    ganaRobot: params.get("gana") === "robot",
    record: params.get("record") === "1",
    incompleta: params.get("incompleta") === "1",
  };
  let junta = op.junta;
  let top = TOP_BASE.map((r) => ({ ...r }));
  let ultimoResultado = null;

  // --- control del guion -------------------------------------------------------------------------------------------
  let cancelables = [];
  const esperandoOrden = new Map();
  let siguiente = null;

  const emitir = (msg) => recibir(msg);
  function esperar(ms) {
    return new Promise((resolver, rechazar) => {
      const id = setTimeout(() => { cancelables = cancelables.filter((c) => c !== cancelar); resolver(); }, ms);
      const cancelar = () => { clearTimeout(id); rechazar(new Saltar()); };
      cancelables.push(cancelar);
    });
  }
  /** Espera una orden de la tablet (o `ms`): resuelve con el mensaje o null. */
  function orden(nombre, ms) {
    return new Promise((resolver, rechazar) => {
      const id = setTimeout(() => { limpiar(); resolver(null); }, ms);
      const limpiar = () => { esperandoOrden.delete(nombre); cancelables = cancelables.filter((c) => c !== cancelar); };
      const cancelar = () => { clearTimeout(id); esperandoOrden.delete(nombre); rechazar(new Saltar()); };
      cancelables.push(cancelar);
      esperandoOrden.set(nombre, (msg) => { clearTimeout(id); limpiar(); resolver(msg); });
    });
  }
  function saltar(a = null) {
    siguiente = a;
    const cs = cancelables;
    cancelables = [];
    cs.forEach((c) => c());
  }
  const di = (frase, emocion = "alegre") => emitir({ tipo: "personaje", frase, emocion, nombre: PERSONAJE.nombre });
  const clic = (sel) => document.querySelector(sel)?.click();

  // --- lo que la tablet manda --------------------------------------------------------------------------------------
  function enviar(msg) {
    const espera = esperandoOrden.get(msg.orden);
    if (espera) { espera(msg); return; }
    if (msg.orden === "jugar") saltar("pedir");
    else if (msg.orden === "monto_yo") saltar("plan_b");
    else if (msg.orden === "reiniciar") saltar("atraccion");
    else if (msg.orden === "voz") interpretar(msg.texto).then((i) => i.confirmable &&
      emitir({ tipo: "orden_propuesta", texto_oido: msg.texto, orden: i.orden, pregunta: i.pregunta }));
  }

  // `/api/voz` simulado (mismo formato que lewelder/voz.py)
  async function interpretar(texto) {
    await new Promise((r) => setTimeout(r, 350));
    const t = texto.toLowerCase();
    const ordenOida = /esquina/.test(t) ? "monta una unión en esquina"
      : /\bt\b|\bte\b|en t\b/.test(t) ? "monta una unión en T" : null;
    if (!ordenOida) {
      return { texto, orden: null, confianza: 0.2, origen: "reglas", aclaracion: null, botones: [], permitida: true,
        confirmable: false, pregunta: null, motivo: "no_entendido",
        respuesta: "No te he pillado: pídeme una T o una esquina.", personaje: PERSONAJE };
    }
    return { texto, orden: ordenOida, confianza: 0.95, origen: "reglas", aclaracion: null, botones: [], permitida: true,
      confirmable: true, pregunta: PREGUNTAS[ordenOida], motivo: "confirmar", nivel: 1,
      respuesta: "Toca Sí y me pongo manos a la obra.", personaje: PERSONAJE };
  }
  // el juez "habla" (si la tablet no tiene reconocimiento o en la maqueta)
  function simularVoz(alParcial) {
    let parar = null;
    const p = new Promise((resolver, rechazar) => {
      const trozos = ["Móntame…", "Móntame una…", "¡Móntame una esquina!"];
      const ids = trozos.map((t, i) => setTimeout(() => alParcial(t), 350 + i * 450));
      const fin = setTimeout(() => resolver({ texto: junta === "t" ? "¡Móntame una T!" : "¡Móntame una esquina!", alternativas: [] }), 1600);
      parar = () => { ids.forEach(clearTimeout); clearTimeout(fin); rechazar(new Error("no-speech")); };
    });
    p.parar = () => parar();
    return p;
  }

  // Vista falsa de la cámara de la muñeca (para el "DETALLE A" del montaje).
  const lienzo = document.createElement("canvas");
  lienzo.width = 320; lienzo.height = 240;
  function imagenCamara(p) {
    const x = lienzo.getContext("2d");
    x.fillStyle = "#3b3f45"; x.fillRect(0, 0, 320, 240);
    x.fillStyle = "#55595f"; for (let i = 0; i < 320; i += 20) x.fillRect(i, 0, 1, 240);
    x.fillStyle = "#c9ccd1"; x.fillRect(150, 70, 150, 60); // base
    x.fillStyle = "#111"; x.fillRect(260, 100, 22, 22); // ArUco
    x.fillStyle = "#fff"; x.fillRect(266, 106, 8, 8);
    const k = Math.min(1, Math.max(0, (p - 0.2) / 0.8));
    const cx = 70 + k * 155, cy = 170 - k * 70 - Math.sin(k * Math.PI) * 30;
    x.save(); x.translate(cx, cy); x.rotate((1 - k) * 0.5);
    x.fillStyle = "#e5e7ea"; x.fillRect(-52, -10 + k * 4, 104, 20 - k * 12);
    x.fillStyle = "#d33"; x.fillRect(-36, -18, 30, 8); // aleta
    x.restore();
    x.strokeStyle = "#47d16b"; x.lineWidth = 2; x.strokeRect(cx - 60, cy - 26, 120, 50);
    x.fillStyle = "#47d16b"; x.font = "14px monospace"; x.fillText(`chapa ${(0.9 + 0.08 * Math.random()).toFixed(2)}`, cx - 58, cy - 30);
    x.fillStyle = "#fff"; x.fillText("CAM MUÑECA · 30 fps", 8, 18);
    return lienzo.toDataURL("image/jpeg", 0.7).split(",")[1];
  }

  // --- escenas -----------------------------------------------------------------------------------------------------
  const ESCENAS = {
    async atraccion() {
      emitir({ tipo: "ranking", top });
      emitir({ tipo: "pantalla", nombre: "atraccion" });
      await esperar(600);
      di("¡Soy Chispas, el robot soldador más rápido del taller!", "chulo");
      if (await orden("jugar", 8400)) return "pedir";
      return "pedir";
    },

    async pedir() {
      emitir({ tipo: "pantalla", nombre: "pedir" });
      await esperar(700);
      di("¿Qué te monto? Pídeme una T o una esquina.", "alegre");
      await esperar(1300);
      clic("#b-micro"); // el juez pulsa el micro y habla
      const conf = await orden("confirmar", 6000);
      if (conf === null) {
        clic("#b-si");
        await esperar(50);
      } else if (!conf.si) {
        di("Vale, no hago nada, tú mandas.", "serio");
        return "pedir";
      }
      const elegida = conf?.orden_confirmada || (junta === "t" ? "monta una unión en T" : "monta una unión en esquina");
      junta = /esquina/.test(elegida) ? "esquina" : "t";
      return "montaje";
    },

    async montaje() {
      emitir({ tipo: "pantalla", nombre: "montaje" });
      di(junta === "t" ? "Marchando una T, mira qué pulso." : "Marchando una esquina, mira qué pulso.", "chulo");
      const fases = ["buscando", "cogiendo", "girando", "encajando"];
      const dur = 11000;
      const t0 = performance.now();
      let ultimaImg = 0;
      while (true) {
        const p = Math.min(1, (performance.now() - t0) / dur);
        const fase = fases[Math.min(3, p < 0.2 ? 0 : p < 0.45 ? 1 : p < 0.75 ? 2 : 3)];
        const msg = { tipo: "robot", tarea: `monta una unión ${junta === "t" ? "en T" : "en esquina"}`, fase, progreso: p };
        if (performance.now() - ultimaImg > 500) { msg.imagen_jpeg_base64 = imagenCamara(p); ultimaImg = performance.now(); }
        emitir(msg);
        if (p >= 1) break;
        await esperar(100);
      }
      di(junta === "t" ? "¡T servida!" : "¡Esquina servida!", "alegre");
      await esperar(1200);
      return "reconocer";
    },

    async plan_b() {
      emitir({ tipo: "pantalla", nombre: "plan_b" });
      di("Vale, móntala tú: yo te miro y te aplaudo.", "alegre");
      await esperar(7000);
      di("¡Eso es! Ya la veo montada.", "sorprendido");
      await esperar(1200);
      return "reconocer";
    },

    async reconocer() {
      emitir({ tipo: "pantalla", nombre: "reconocer" });
      await esperar(500);
      if (op.incompleta) {
        emitir(juntaMsg("incompleta"));
        di("La junta ha quedado a medias, mejor la desmonto y empiezo de nuevo.", "serio");
        await esperar(5000);
        return "montaje";
      }
      emitir(juntaMsg(junta));
      await esperar(1500);
      emitir(op.alcance ? { tipo: "alcance", llega: true }
        : { tipo: "alcance", llega: false, texto: "gírala 90° hacia mí", giro_grados: 90 });
      di(op.alcance ? "Mira aquí: por esta línea va el cordón." : "No llego bien: gira la pieza 90 grados hacia mí, porfa.",
        op.alcance ? "alegre" : "serio");
      await esperar(7000);
      return "demostracion";
    },

    async demostracion() {
      emitir({ tipo: "pantalla", nombre: "demostracion" });
      di("Mira y aprende.", "chulo");
      const dur = 7000;
      const t0 = performance.now();
      while (true) {
        const p = Math.min(1, (performance.now() - t0) / dur);
        emitir({ tipo: "robot", tarea: "coge la antorcha y suelda la junta", fase: "soldando", progreso: p });
        if (p >= 1) break;
        await esperar(50);
      }
      emitir({ tipo: "fantasma", tramos: FANTASMA, duracion: FANTASMA.reduce((s, t) => s + C.TAMANO_TRAMO / t.velocidad, 0) });
      di("Mi cordón es tu fantasma: atrápalo si puedes.", "chulo");
      await esperar(2200);
      return "cuenta_atras";
    },

    async cuenta_atras() {
      emitir({ tipo: "pantalla", nombre: "cuenta_atras" });
      await esperar(3800);
      return "ronda";
    },

    async ronda() {
      emitir({ tipo: "pantalla", nombre: "ronda" });
      if (!ultimoFantasma) emitir({ tipo: "fantasma", tramos: FANTASMA, duracion: 26 });
      ultimoFantasma = true;
      ultimoResultado = await simularRonda();
      return "resultado";
    },

    async resultado() {
      const r = ultimoResultado || resultadoPorDefecto();
      emitir({ tipo: "pantalla", nombre: "resultado" });
      emitir(r);
      await esperar(1900);
      if (r.gana_al_robot) di("Vale, has ganado, pero exijo la revancha.", "picado");
      else di("Robot uno, humano cero: ¿la revancha?", "chulo");
      await esperar(6500);
      return r.entra_en_ranking ? "iniciales" : "ranking";
    },

    async iniciales() {
      emitir({ tipo: "pantalla", nombre: "iniciales" });
      emitir({ tipo: "puntos", total: ultimoResultado?.puntos ?? 0, combo: 0, multiplicador: 1 });
      di("Firma el plano, campeón: tres letras.", "alegre");
      // el juez teclea "ANE" con las flechas (si no lo hace él antes)
      const auto = (async () => {
        await esperar(1200);
        for (let i = 0; i < 13; i++) { clic('.letra[data-i="1"] .abajo'); await esperar(110); }
        await esperar(250);
        for (let i = 0; i < 4; i++) { clic('.letra[data-i="2"] .abajo'); await esperar(140); }
        await esperar(900);
        clic("#b-firmar");
      })().catch(() => {});
      const m = await orden("iniciales", 9000);
      await auto;
      const ini = (m?.texto || "ANE").slice(0, 3).toUpperCase();
      const puntos = ultimoResultado?.puntos ?? 0;
      top.push({ iniciales: ini, puntos, junta });
      top.sort((a, b) => b.puntos - a.puntos);
      const pos = top.findIndex((r) => r.iniciales === ini && r.puntos === puntos) + 1;
      top = top.slice(0, 10);
      emitir({ tipo: "ranking", top, posicion_nueva: pos <= 10 ? pos : null });
      return "ranking";
    },

    async ranking() {
      emitir({ tipo: "pantalla", nombre: "ranking" });
      di("Tu nombre ya está en la pared de los grandes.", "sorprendido");
      if (await orden("jugar", 7000)) return "pedir";
      top = top.map(({ iniciales, puntos, junta: j }) => ({ iniciales, puntos, junta: j }));
      emitir({ tipo: "ranking", top });
      return "atraccion";
    },
  };
  let ultimoFantasma = null;

  // El mensaje se llama `junta` (campo `tipo`) y el tipo de junta va en el campo `junta` (ver PROTOCOLO.md).
  function juntaMsg(t) {
    if (t === "incompleta") {
      return { tipo: "junta", junta: "incompleta", posicion_soldeo: null, confianza: 0.81,
        motivo: "la chapa móvil no apoya en la base", ficha: null };
    }
    return { tipo: "junta", junta: t, posicion_soldeo: "PB", confianza: t === "t" ? 0.96 : 0.97, ficha: FICHAS[t] };
  }

  // --- fantasma del robot: 24 tramos a ~4,6 mm/s y 45° ------------------------------------------------------------
  const FANTASMA = Array.from({ length: C.N_TRAMOS }, (_, i) => ({
    x0: i * C.TAMANO_TRAMO,
    velocidad: +(4.6 + 0.15 * Math.sin(i * 1.7)).toFixed(2),
    angulo: +(45 + 1.5 * Math.sin(i * 0.9)).toFixed(1),
  }));
  function xFantasma(t) {
    let x = 0, resto = t;
    for (const tr of FANTASMA) {
      const dur = C.TAMANO_TRAMO / tr.velocidad;
      if (resto <= dur) return x + resto * tr.velocidad;
      x += C.TAMANO_TRAMO; resto -= dur;
    }
    return C.LONGITUD_CORDON;
  }

  // --- la ronda: el juez suelda (30 Hz) y la maqueta puntúa como lo haría el servidor ------------------------------
  async function simularRonda() {
    const lento = op.ganaRobot;
    // perfil de la pasada: [hasta_x, velocidad mm/s]; con una parada (quemado) en 50 mm y la antorcha despegada en 31-34
    const perfil = lento ? [[40, 4.0], [50, 4.2], [120, 4.3]] : [[40, 4.3], [50, 4.6], [120, 5.9]];
    const dt = 1 / 30;
    let x = 0, t = 0, tCarrera = null;
    let parado = 0, quemadoAvisado = false;
    // Mismas reglas que lewelder/puntuacion.py: 100 x (0,5 + 0,5 x calidad) x combo por tramo; combo x1-x4 cada 4
    // tramos bien seguidos; -500 por quemado; -300 por soldar sin apoyo; ritmo x1-x1,25 y +1.000 si gana al robot.
    let total = 0, combo = 0, multi = 1;
    let sinApoyoAvisado = false;
    const tramos = new Array(C.N_TRAMOS).fill(null);
    let tramoActual = 0, peorTramo = null;
    let ibaGanando = "robot", adelantado = false;
    let ultimoVivo = 0;
    const PEOR = { bien: 0, regular: 1, quemado: 2 };
    const t0 = performance.now();

    const CALIDAD = { bien: 0.96, regular: 0.6, quemado: 0.3 };
    const cerrarTramo = (i, c) => {
      tramos[i] = c || "suelto";
      let evento = null;
      const q = CALIDAD[c] ?? 0;
      if (c === "bien") {
        combo++;
        const nuevo = Math.min(4, 1 + Math.floor((combo - 1) / 4));
        if (nuevo > multi) evento = { texto: `COMBO x${nuevo}`, tipo: "bueno" };
        multi = nuevo;
        total += Math.round(100 * (0.5 + 0.5 * q) * multi);
      } else {
        if (combo >= 4) evento = { texto: "COMBO ROTO", tipo: "malo" };
        combo = 0; multi = 1;
        if (q > 0) total += Math.round(100 * (0.5 + 0.5 * q));
      }
      emitir({ tipo: "puntos", total, combo, multiplicador: multi, ...(evento ? { evento } : {}) });
    };

    while (x < C.LONGITUD_CORDON) {
      // reloj real para que la ronda dure lo que dura
      const ahora = (performance.now() - t0) / 1000;
      while (t < ahora && x < C.LONGITUD_CORDON) {
        t += dt;
        let gatillo = t > 0.6;
        let v = 0;
        if (gatillo) v = perfil.find(([hasta]) => x < hasta)[1];
        // parada de 1 s en 50,5 mm → quemado
        if (x >= 50.5 && parado < 1.0) { v = 0.25; parado += dt; }
        const apoyada = !(x >= 31 && x < 34);
        x = Math.min(C.LONGITUD_CORDON, x + v * dt);
        let calidad = "bien";
        if (!apoyada) calidad = "suelto";
        else if (x >= 34 && x < 35) calidad = "regular";
        else if (parado > 0 && parado < 1.0 && x >= 50.5) calidad = parado > 0.6 ? "quemado" : "regular";
        if (lento && x > 70 && x < 80) calidad = "regular";
        if (gatillo && apoyada && tCarrera == null) tCarrera = t;
        if (gatillo && !apoyada && x > 31.8 && !sinApoyoAvisado) {
          sinApoyoAvisado = true;
          total = Math.max(0, total - 300);
          emitir({ tipo: "puntos", total, combo, multiplicador: multi, evento: { texto: "¡APOYA LA ANTORCHA!", tipo: "malo" } });
        }
        // quemado: aviso al pasar 0,6 s parado
        if (parado > 0.6 && !quemadoAvisado) {
          quemadoAvisado = true;
          combo = 0; multi = 1; total = Math.max(0, total - 500);
          emitir({ tipo: "puntos", total, combo, multiplicador: multi, evento: { texto: "¡QUEMADO!", tipo: "malo" } });
          di("¡Uy, eso huele a chamusquina!", "sorprendido");
        }
        // tramo
        const i = Math.min(C.N_TRAMOS - 1, Math.floor(x / C.TAMANO_TRAMO));
        if (i !== tramoActual) { cerrarTramo(tramoActual, peorTramo); tramoActual = i; peorTramo = null; }
        if (gatillo && apoyada && (peorTramo == null || PEOR[calidad] > PEOR[peorTramo])) peorTramo = calidad;
        // muestra (30 Hz)
        const y = 0.9 * Math.sin(t * 2.1) + 0.4 * Math.sin(t * 7.3);
        emitir({ tipo: "muestra", t: +t.toFixed(3), x: +x.toFixed(2), y: +y.toFixed(2), z: apoyada ? 0.8 : 9,
          apoyada, gatillo, calidad: gatillo ? calidad : "suelto" });
        // carrera contra el fantasma
        if (tCarrera != null && t - ultimoVivo > 0.25) {
          ultimoVivo = t;
          const xf = xFantasma(t - tCarrera);
          const ventaja = x - xf;
          const va = ventaja >= 0 ? "juez" : "robot";
          emitir({ tipo: "fantasma_vivo", ventaja_mm: +ventaja.toFixed(1), ventaja_s: +(ventaja / 4.6).toFixed(2), va_ganando: va });
          if (va === "juez" && ibaGanando === "robot" && !adelantado && x > 20) {
            adelantado = true;
            emitir({ tipo: "puntos", total, combo, multiplicador: multi, evento: { texto: "¡ADELANTAS AL ROBOT!", tipo: "epico" } });
            di("¡Eh, eh, no corras tanto!", "picado");
          }
          ibaGanando = va;
        }
      }
      await esperar(33);
    }
    cerrarTramo(tramoActual, peorTramo);
    await esperar(500);
    const ritmo = lento ? 1.04 : 1.12;
    total = Math.round(total * ritmo);
    emitir({ tipo: "puntos", total, combo, multiplicador: multi, evento: { texto: `RITMO x${ritmo.toFixed(2)}`, tipo: "bueno" } });
    await esperar(900);
    const gana = !lento;
    if (gana) {
      total += 1000;
      emitir({ tipo: "puntos", total, combo, multiplicador: multi, evento: { texto: "¡HAS GANADO AL ROBOT!", tipo: "epico" } });
      await esperar(1200);
    }
    const puntosFinal = total;
    const record = op.record || puntosFinal > top[0].puntos;
    return {
      tipo: "resultado",
      puntos: puntosFinal,
      nota: lento ? 6.4 : 7.8,
      metricas: { cobertura: 0.98, ritmo: lento ? 0.66 : 0.82, quemados: 1, desvio: 1.6, angulo: 47, apoyo: 0.95 },
      tramos,
      gana_al_robot: gana,
      record,
      entra_en_ranking: puntosFinal > top[top.length - 1].puntos,
      insignia: gana ? { nombre: `Oficial de ${junta === "t" ? "T" : "esquina"}`, nivel: "oficial" } : null,
    };
  }
  function resultadoPorDefecto() {
    return {
      tipo: "resultado", puntos: op.ganaRobot ? 4380 : 7140, nota: op.ganaRobot ? 6.4 : 7.8,
      metricas: { cobertura: 0.98, ritmo: 0.82, quemados: 1, desvio: 1.6, angulo: 47, apoyo: 0.95 },
      tramos: Array.from({ length: 24 }, (_, i) => (i === 10 ? "quemado" : i === 6 ? "regular" : "bien")),
      gana_al_robot: !op.ganaRobot, record: op.record, entra_en_ranking: true,
      insignia: op.ganaRobot ? null : { nombre: `Oficial de ${junta === "t" ? "T" : "esquina"}`, nivel: "oficial" },
    };
  }

  // --- arranque ----------------------------------------------------------------------------------------------------
  conectar({ enviar, saltar: () => saltar(null), interpretar, simularVoz });
  const ORDEN = ["atraccion", "pedir", "montaje", "reconocer", "demostracion", "cuenta_atras", "ronda", "resultado",
    "iniciales", "ranking"];
  let actual = ESCENAS[inicio] ? inicio : "atraccion";
  // al empezar a mitad de partida, la tablet necesita lo que ya habría recibido antes
  emitir({ tipo: "ranking", top });
  if (ORDEN.indexOf(actual) > ORDEN.indexOf("reconocer") || actual === "plan_b") emitir(juntaMsg(junta));
  if (ORDEN.indexOf(actual) > ORDEN.indexOf("demostracion")) {
    emitir({ tipo: "fantasma", tramos: FANTASMA, duracion: 26 });
    ultimoFantasma = true;
  }
  if (actual === "ranking") {
    top.splice(2, 0, { iniciales: "ANE", puntos: 7140, junta });
    top = top.slice(0, 10);
    emitir({ tipo: "ranking", top, posicion_nueva: 3 });
  }
  if (actual === "iniciales") ultimoResultado = resultadoPorDefecto();
  if (actual === "pedir" || actual === "montaje") recibir({ tipo: "pantalla", nombre: "atraccion" });

  (async () => {
    while (true) {
      let prox;
      try {
        prox = await ESCENAS[actual]();
      } catch (e) {
        if (!(e instanceof Saltar)) console.error(e);
        prox = null;
      }
      if (siguiente) { prox = siguiente; siguiente = null; }
      if (!prox) {
        const i = ORDEN.indexOf(actual);
        prox = i >= 0 ? ORDEN[(i + 1) % ORDEN.length] : "reconocer";
      }
      actual = prox;
    }
  })();
}
