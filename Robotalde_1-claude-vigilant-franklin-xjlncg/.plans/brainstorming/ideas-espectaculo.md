# Ideas · lente espectáculo y juego

Generadas por un agente independiente con solo [contexto-abstracto.md](contexto-abstracto.md) y una búsqueda rápida
(no aparecieron proyectos con SO-101 de bomba, magia ni juego de la rana; búsqueda superficial).

| # | Idea | Frase | Órdenes del VLA | Momento memorable | Físico propio | Riesgo | Filtro |
|---|---|---|---|---|---|---|---|
| G1 | **Desactívame** (bomba cooperativa) | El juez lee el manual, el robot corta los cables: 90 segundos | saca el fusible {color} · mételo en el zócalo {A/B} · pulsa el botón | Al fallar, la "bomba" suelta confeti y el personaje se disculpa | Caja con fusibles enchufables, LED, zumbador, ESP32 que sabe qué falta | Distinguir fusibles por color en la misma escena (dar forma y posición distintas) | 6 ✓ 1 ~ |
| G2 | **Txapeldun de la Rana** (duelo en el juego de la rana) | El juego de la rana de los bares vascos: el juez contra el robot | coge una chapa · métela en la boca de la rana · en el molino | El robot acierta en la boca y el personaje se burla como un comentarista de bar | Rana con embudos y sensores IR por agujero | Utilidad baja; puede verse como juguete | 6 ✓ 1 ~ |
| G3 | El Mago (truco de cartas) | Escoge una carta, escóndela; el robot te la devuelve | abre la caja {n} · coge la carta · entrégala | Abre la caja correcta y entrega la carta | Cajas con asa, cartas gruesas, chistera | Tapa y carta plana: difícil y larga | 4 ✓ 3 ~ |
| G4 | Regateo en La Ribera (vendedor del mercado) | Pídele un pimiento al robot... y regatea | coge {producto} a la bandeja · moneda a la caja · devuelve al puesto | El robot "se enfada" pero vende, o devuelve el producto | Puesto, productos, monedas, báscula | Parecido a tienda / camarero | 6 ✓ 1 ~ |
| G5 | Lokotx Bilketa (deporte rural) | Carrera de recoger mazorcas: el robot contra el juez | coge la mazorca más cercana · échala en la cesta | Llegada ajustada con narrador | Mazorcas, cesta con báscula | No parece difícil | 6 ✓ 1 ✗ |

**Favorita del generador: G1 (Desactívame)**. Juez en el centro con tensión real; el ESP32 verifica cada paso
(estados visibles, aciertos medidos, reintento dentro del juego).
