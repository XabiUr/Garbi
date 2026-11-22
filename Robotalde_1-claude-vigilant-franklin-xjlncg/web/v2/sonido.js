// Sonido de la recreativa, todo sintetizado con Web Audio (sin archivos).
//
// - arco(nivel, calidad): zumbido del arco mientras se suelda (sierra grave + ruido filtrado) y chisporroteo.
// - efectos de una vez: toque, combo(n), quemado, error, cuenta(n), suelda, fanfarria, puntos, sello, robot.
// - musica(true/false): bucle de atracción opcional (bajo y arpegio de onda cuadrada, muy bajito).
// El navegador no deja sonar nada hasta el primer toque: `despertar()` va en el primer pointerdown.

const CLAVE_SILENCIO = "lewelder.v2.silencio";

export function crearSonido() {
  let ctx = null;
  let maestro = null;
  let silencio = false;
  try { silencio = localStorage.getItem(CLAVE_SILENCIO) === "1"; } catch (e) { /* sin almacenamiento */ }
  let ruido = null;
  let arcoNodos = null;
  let musica = null;

  function despertar() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      ctx = new AC();
      maestro = ctx.createGain();
      maestro.gain.value = silencio ? 0 : 0.8;
      const comp = ctx.createDynamicsCompressor();
      comp.threshold.value = -14;
      comp.ratio.value = 4;
      maestro.connect(comp).connect(ctx.destination);
      // 2 s de ruido blanco reutilizable
      ruido = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
      const d = ruido.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    if (ctx.state === "suspended") ctx.resume();
    return true;
  }
  const listo = () => ctx && ctx.state === "running";

  function tono(frec, { t = 0, dur = 0.12, tipo = "square", vol = 0.2, hasta = null, ataque = 0.005 } = {}) {
    if (!listo()) return;
    const t0 = ctx.currentTime + t;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = tipo;
    o.frequency.setValueAtTime(frec, t0);
    if (hasta) o.frequency.exponentialRampToValueAtTime(hasta, t0 + dur);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(vol, t0 + ataque);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    o.connect(g).connect(maestro);
    o.start(t0);
    o.stop(t0 + dur + 0.02);
  }
  function rafaga({ t = 0, dur = 0.08, vol = 0.3, filtro = 3000, q = 1, tipo = "bandpass" } = {}) {
    if (!listo()) return;
    const t0 = ctx.currentTime + t;
    const s = ctx.createBufferSource();
    s.buffer = ruido;
    const f = ctx.createBiquadFilter();
    f.type = tipo;
    f.frequency.value = filtro;
    f.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(vol, t0);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    s.connect(f).connect(g).connect(maestro);
    s.start(t0, Math.random() * 1.5);
    s.stop(t0 + dur + 0.02);
  }

  // --- arco continuo ---------------------------------------------------------------------------------------------
  function crearArco() {
    const sierra = ctx.createOscillator();
    sierra.type = "sawtooth";
    sierra.frequency.value = 100;
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 50;
    const lfoG = ctx.createGain();
    lfoG.gain.value = 6;
    lfo.connect(lfoG).connect(sierra.frequency);
    const gSierra = ctx.createGain();
    gSierra.gain.value = 0.05;
    const n = ctx.createBufferSource();
    n.buffer = ruido;
    n.loop = true;
    const fn = ctx.createBiquadFilter();
    fn.type = "bandpass";
    fn.frequency.value = 2400;
    fn.Q.value = 0.7;
    const gRuido = ctx.createGain();
    gRuido.gain.value = 0.25;
    const salida = ctx.createGain();
    salida.gain.value = 0;
    sierra.connect(gSierra).connect(salida);
    n.connect(fn).connect(gRuido).connect(salida);
    salida.connect(maestro);
    sierra.start(); lfo.start(); n.start();
    let crepitar = null;
    return {
      salida, fn, sierra,
      set crepitar(v) { crepitar = v; },
      get crepitar() { return crepitar; },
    };
  }
  let chisporroteo = 0;
  function arco(nivel, calidad = "bien") {
    if (!listo()) return;
    if (!arcoNodos) arcoNodos = crearArco();
    const t = ctx.currentTime;
    const objetivo = nivel ? (calidad === "quemado" ? 0.5 : 0.32) : 0;
    arcoNodos.salida.gain.setTargetAtTime(objetivo, t, nivel ? 0.02 : 0.06);
    arcoNodos.fn.frequency.setTargetAtTime(calidad === "quemado" ? 900 : calidad === "regular" ? 1700 : 2600, t, 0.05);
    arcoNodos.sierra.frequency.setTargetAtTime(calidad === "quemado" ? 70 : 100, t, 0.05);
    // chisporroteo: chasquidos sueltos mientras hay arco
    if (nivel && t > chisporroteo) {
      const n = calidad === "bien" ? 5 : 2;
      for (let i = 0; i < n; i++) rafaga({ t: Math.random() * 0.1, dur: 0.012 + Math.random() * 0.02, vol: 0.18 + Math.random() * 0.2, filtro: 3000 + Math.random() * 4000, q: 2 });
      chisporroteo = t + 0.1;
    }
  }

  // --- efectos ---------------------------------------------------------------------------------------------------
  const NOTAS = [523.25, 659.25, 783.99, 1046.5, 1318.5, 1568];
  const efectos = {
    toque() { tono(1200, { dur: 0.04, vol: 0.12, tipo: "square" }); },
    puntos() { tono(1760, { dur: 0.03, vol: 0.05, tipo: "square" }); },
    combo(n = 4) {
      const pasos = Math.min(6, 2 + Math.floor(n / 4));
      for (let i = 0; i < pasos; i++) tono(NOTAS[i], { t: i * 0.055, dur: 0.09, vol: 0.16 });
    },
    quemado() {
      tono(220, { dur: 0.45, tipo: "sawtooth", vol: 0.28, hasta: 55 });
      tono(233, { dur: 0.45, tipo: "square", vol: 0.12, hasta: 58 });
      rafaga({ dur: 0.35, vol: 0.4, filtro: 600, q: 0.6, tipo: "lowpass" });
    },
    error() { tono(180, { dur: 0.16, tipo: "square", vol: 0.18 }); tono(140, { t: 0.17, dur: 0.22, tipo: "square", vol: 0.18 }); },
    aviso() { tono(880, { dur: 0.07, vol: 0.12 }); tono(880, { t: 0.12, dur: 0.07, vol: 0.12 }); },
    cuenta() { tono(660, { dur: 0.18, vol: 0.22, tipo: "square" }); },
    suelda() {
      tono(1320, { dur: 0.5, vol: 0.22, tipo: "square" });
      tono(660, { dur: 0.5, vol: 0.14, tipo: "sawtooth" });
      rafaga({ dur: 0.5, vol: 0.35, filtro: 2500, q: 0.5 });
    },
    sello() { rafaga({ dur: 0.09, vol: 0.5, filtro: 220, q: 0.8, tipo: "lowpass" }); tono(90, { dur: 0.1, tipo: "sine", vol: 0.3, hasta: 50 }); },
    epico() {
      [0, 4, 7, 12].forEach((s, i) => tono(392 * 2 ** (s / 12), { t: i * 0.07, dur: 0.16, vol: 0.18 }));
      tono(784 * 2, { t: 0.3, dur: 0.4, vol: 0.14, tipo: "triangle" });
    },
    fanfarria() {
      const m = [[523, 0], [523, 0.12], [523, 0.24], [659, 0.36], [784, 0.6], [659, 0.84], [784, 0.96], [1046, 1.2]];
      for (const [f, t] of m) { tono(f, { t, dur: 0.2, vol: 0.18 }); tono(f / 2, { t, dur: 0.2, vol: 0.08, tipo: "triangle" }); }
      tono(1046, { t: 1.2, dur: 0.9, vol: 0.16, tipo: "square" });
      tono(523, { t: 1.2, dur: 0.9, vol: 0.12, tipo: "triangle" });
    },
    risa() {
      // el robot se ríe: "ja-ja-ja" en onda cuadrada que baja
      for (let i = 0; i < 4; i++) tono(700 - i * 60, { t: i * 0.13, dur: 0.09, vol: 0.14, hasta: 500 - i * 60 });
    },
    robot() { tono(300, { dur: 0.06, vol: 0.08, hasta: 600 }); tono(600, { t: 0.07, dur: 0.06, vol: 0.08, hasta: 400 }); },
    barrido() { rafaga({ dur: 0.28, vol: 0.12, filtro: 1800, q: 6 }); },
  };

  // --- música de atracción (opcional, muy bajita) ----------------------------------------------------------------
  function bucleMusica() {
    if (!musica) return;
    if (!listo()) { musica = setTimeout(bucleMusica, 1000); return; }
    const bajo = [110, 110, 146.8, 130.8];
    const arp = [440, 523.25, 659.25, 523.25];
    const paso = 0.22;
    for (let c = 0; c < 4; c++) {
      for (let i = 0; i < 8; i++) {
        const t = (c * 8 + i) * paso;
        if (i % 2 === 0) tono(bajo[c], { t, dur: paso * 1.6, vol: 0.05, tipo: "triangle" });
        tono(arp[(i + c) % 4] * (c === 2 ? 1.122 : 1), { t, dur: paso * 0.6, vol: 0.02, tipo: "square" });
      }
    }
    musica = setTimeout(bucleMusica, 32 * paso * 1000);
  }

  return {
    despertar,
    ...efectos,
    arco,
    musica(si) {
      if (si && !musica) { musica = true; bucleMusica(); }
      if (!si && musica) { clearTimeout(musica); musica = null; }
    },
    get silencio() { return silencio; },
    set silencio(v) {
      silencio = v;
      try { localStorage.setItem(CLAVE_SILENCIO, v ? "1" : "0"); } catch (e) { /* sin almacenamiento */ }
      if (maestro) maestro.gain.setTargetAtTime(v ? 0 : 0.8, ctx.currentTime, 0.02);
      if (v && "speechSynthesis" in window) speechSynthesis.cancel();
    },
  };
}
