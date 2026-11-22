// Voz de la tablet v2: oír al juez (Web Speech API, es-ES), interpretar con `POST /api/voz` (tarea 3) y hacer
// hablar a Chispas. Reutiliza `hablarComoPersonaje` del componente v1 (`web/voz.js`); la tarjeta y el micrófono
// son los de la estética de plano (en `app.js`).

import { hablarComoPersonaje } from "../voz.js";

export const PERSONAJE = { nombre: "Chispas", voz: { lang: "es-ES", rate: 1.12, pitch: 1.35 } };

const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
export const hayReconocimiento = Boolean(SR);

/**
 * Escucha una frase. `alParcial(texto)` recibe lo que va oyendo; la promesa resuelve con
 * `{texto, alternativas}` o rechaza con un Error cuyo `message` es el código (`no-speech`, `not-allowed`...).
 */
export function escuchar(alParcial = () => {}) {
  let rec = null;
  const promesa = new Promise((resolver, rechazar) => {
    if (!SR) { rechazar(new Error("sin-reconocimiento")); return; }
    if ("speechSynthesis" in window) speechSynthesis.cancel(); // que Chispas no se oiga a sí mismo
    rec = new SR();
    rec.lang = "es-ES";
    rec.interimResults = true;
    rec.maxAlternatives = 3;
    rec.continuous = false;
    let hecho = false;
    rec.onresult = (ev) => {
      const r = ev.results[ev.results.length - 1];
      alParcial(r[0].transcript);
      if (r.isFinal && !hecho) {
        hecho = true;
        resolver({ texto: r[0].transcript, alternativas: Array.from(r).slice(1).map((a) => a.transcript) });
      }
    };
    rec.onerror = (ev) => { if (!hecho) { hecho = true; rechazar(new Error(ev.error || "error")); } };
    rec.onend = () => { if (!hecho) { hecho = true; rechazar(new Error("no-speech")); } };
    try { rec.start(); } catch (e) { hecho = true; rechazar(new Error("no-disponible")); }
  });
  promesa.parar = () => { try { rec?.stop(); } catch (e) { /* ya parado */ } };
  return promesa;
}

/** Interpreta una frase con el servidor (`POST /api/voz`). Devuelve la interpretación o lanza si no hay servidor. */
export async function interpretar(texto, alternativas = [], contexto = null) {
  const r = await fetch(new URL("/api/voz", location.href), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto, alternativas, ...(contexto ? { contexto } : {}) }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

/** Chispas habla (si no hay silencio). */
export function decir(texto, { silencio = false, personaje = PERSONAJE, alTerminar = null } = {}) {
  if (silencio || !texto) return false;
  return hablarComoPersonaje(texto, personaje.voz, alTerminar);
}
