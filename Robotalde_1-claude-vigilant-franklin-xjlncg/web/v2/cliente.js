// Cliente real de la tablet v2: WebSocket `/ws2` del servidor (protocolo en PROTOCOLO.md). Reconecta solo.
// Mientras no hay servidor, la tablet se queda en la pantalla de atracción con el aviso "SIN CONEXIÓN".

export function arrancarCliente({ recibir, conectar, conexion }) {
  let ws = null;
  let espera = 500;
  const cola = []; // órdenes enviadas sin conexión (se mandan al reconectar, solo las últimas)

  function enviar(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
    else { cola.push(obj); if (cola.length > 5) cola.shift(); }
  }

  function abrir() {
    const url = new URL("/ws2", location.href);
    // Simulador con varias partidas: la tablet se une a la de su página (`?partida=ID`).
    const partida = new URLSearchParams(location.search).get("partida");
    if (partida) url.searchParams.set("partida", partida);
    url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(url);
    ws.onopen = () => {
      espera = 500;
      conexion(true);
      while (cola.length) ws.send(JSON.stringify(cola.shift()));
    };
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (Array.isArray(msg)) msg.forEach(recibir);
      else recibir(msg);
    };
    ws.onclose = () => {
      conexion(false);
      setTimeout(abrir, espera);
      espera = Math.min(5000, espera * 1.6);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) { /* ya cerrado */ } };
  }

  conectar({ enviar });
  recibir({ tipo: "pantalla", nombre: "atraccion" });
  abrir();
}
