# Ideas · lente industria y dificultad técnica

Generadas por un agente independiente con solo [contexto-abstracto.md](contexto-abstracto.md). Novedad estimada,
sin buscar en internet.

| # | Idea | Frase | Órdenes del VLA | Momento memorable | Físico propio | Riesgo | Filtro |
|---|---|---|---|---|---|---|---|
| I1 | **GalgaBot** (calidad pasa / no pasa) | El robot mete cada pieza en la galga y aparta la defectuosa | mete en la galga · deja en OK · deja en rechazo | El jurado mete una pieza trucada (1 mm más gruesa) y la galga se pone en rojo | Galga con embudo y microinterruptor (ESP32), piezas buenas y malas | Insertar en la galga pide precisión: chaflán grande, ~3 mm de tolerancia | 6 ✓ 1 ~ |
| I2 | **Kanban-Bot** (reposición de línea) | Tú montas, el robot nunca te deja sin piezas | retira la caja vacía · pon la caja llena en la estación | El juez vacía la caja con prisa y el robot la cambia antes de que la pida | Cajas con asa, estantería inclinada, báscula con ESP32 | Dos órdenes parecidas en la misma escena | 6 ✓ 1 ~ |
| I3 | **Pañol** (panel de sombras de mantenimiento) | Dile qué avería vas a reparar y te prepara el kit | coge la llave / el extractor y déjalo en la bandeja · devuelve a su sombra | El juez "olvida" una herramienta y el personaje la reclama ("te falta la llave del 13") | Panel de sombras, herramientas impresas con asa | Coger herramientas finas (mango alto) | 7 ✓ |
| I4 | **Relevo** (cambio de módulo averiado) | La fábrica en miniatura se apaga y el robot cambia el relé fundido | saca el módulo averiado a reciclaje · mete uno nuevo en el hueco | El robot cambia el módulo y la maqueta vuelve a encenderse | Cuadro con huecos-embudo e imanes, módulos con pogo pins, maqueta con LED y motor | La inserción tiene que hacer contacto eléctrico | 6 ✓ 1 ~ |
| I5 | Vivero (repicado) | Pasa a maceta solo las semillas que han brotado | plántula a maceta · alvéolo vacío al compost | El juez mezcla y el robot repica las buenas | Bandeja alveolar, cepellones, macetas | Parece clasificar por colores disfrazado | 5 ✓ 2 ~ |

**Favorita del generador: I4 (Relevo)**. La avería que provoca el jurado y la fábrica que vuelve a encenderse se
entienden en 5 s, y el ESP32 confirma cada paso. Alternativa segura: I3 (Pañol), que solo es coger y dejar.
