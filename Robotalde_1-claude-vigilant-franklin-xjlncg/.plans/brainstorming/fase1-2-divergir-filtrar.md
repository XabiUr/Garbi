# Brainstorming · fases 1 y 2: divergir y filtrar (18-11-2026)

Método: skill `council` de ecc aplicada a mano (las skills del equipo no se cargan en la nube). Contexto común en
[contexto.md](contexto.md).

## Fase 1 · Direcciones posibles

| # | Dirección | Qué hace el robot (aprendido) | Qué hace el humano | Tema |
|---|---|---|---|---|
| D1 | **LeWelder v2 recortado** | Monta la junta pedida por voz (T / esquina) con SmolVLA; demuestra la soldadura con replay | Pide la junta y suelda con la antorcha; recibe nota | Escuela de soldadura |
| D2 | **Carrera humano contra robot** | Monta juntas por voz con SmolVLA, con reintento si falla el agarre | Monta la misma junta a contrarreloj; la escuela mide tiempo y calidad (ArUco) y declara ganador | Taller arcade |
| D3 | **Aprendiz del soldador ("pásame...")** | Coge y entrega por voz las herramientas del puesto (antorcha, cepillo, piqueta, careta) y las recoge | Suelda la junta y pide lo que necesita | Ayudante de taller |
| D4 | Posicionador | Orienta la junta en la posición de soldeo pedida ("ponla en horizontal") | Suelda en la posición cómoda | Ayudante industrial |
| D5 | Inspector de calidad | Aparta las piezas con el defecto que se le dice ("las que tienen poros") | Suelda / revisa; discute con el robot | Control de calidad |
| D6 | El robot aprende en la escuela | Practica solo (recolector), la escuela puntúa cada intento y solo aprende de los buenos | Ve su progreso; compite con él | Narrativa transversal |
| D7 | Punteador | Hace puntos de soldadura donde el juez señala | Señala | Soldadura robotizada |
| D8 | Cambiar de tema | — | — | Otro |

## Fase 2 · Filtro de 7 puntos y riesgos

✓ cumple · ~ a medias · ✗ no cumple

| Criterio | D1 | D2 | D3 | D4 | D5 | D7 |
|---|---|---|---|---|---|---|
| 1. Habilidad central al 80 % con 50-80 episodios | ~ montar es difícil (aleta, giro, imanes) | ~ igual que D1 | ✓ coger y dejar objetos distintos | ~ girar sujetando | ✗ distinguir defectos pequeños | ✗ precisión (imitación no da ±5 mm) |
| 2. Parece difícil | ✓ | ✓ | ~ "pasar cosas" parece fácil | ✓ | ✓ | ✓ |
| 3. 5 s y humano en el centro | ~ la clase es larga | ✓ duelo inmediato | ✓ | ~ | ~ | ✓ |
| 4. Recuperación planificada | ✓ reintentar agarre | ✓ reintento visible en la carrera | ✓ objeto caído | ~ | ~ | ✗ |
| 5. Capa de vida quitable | ✓ Chispas | ✓ Chispas pica al juez | ✓ | ✓ | ✓ | ✓ |
| 6. Algo físico propio | ✓ piezas con imanes, antorcha | ✓ piezas con imanes | ✓ herramientas impresas | ✓ | ✓ | ~ |
| 7. Escalera de alcance | ✓ | ✓ | ✓ | ~ | ~ | ✗ |
| **Total** | 5 ✓ 2 ~ | 6 ✓ 1 ~ | 6 ✓ 1 ~ | 3 ✓ 4 ~ | 3 ✓ 3 ~ 1 ✗ | 3 ✓ 1 ~ 3 ✗ |
| Fuerza VLA (varias órdenes, misma escena) | media (2 órdenes parecidas) | media | **alta** (4-5 objetos distintos) | media | alta, pero frágil | baja |
| Dependencia de la antorcha seguida por visión | **alta** (núcleo) | baja (opcional) | media | media | baja | baja |
| Parecido con MSN (soldadura, ayudante) | bajo | bajo | **alto** ("tercera mano") | medio | bajo | medio |
| Reutiliza lo hecho | máximo | alto | medio | medio | bajo | bajo |

Descartadas: **D4** (sujetar mientras se suelda pide par y es parecido a MSN), **D5** (percepción de defectos
pequeños poco fiable con SmolVLA), **D7** (la imitación no da la precisión), **D8** (se tira todo lo hecho a 2 días).
**D6** no es una demo sino una narrativa: se puede añadir a cualquiera.

**Finalistas para el consejo: D1, D2 y D3.**
