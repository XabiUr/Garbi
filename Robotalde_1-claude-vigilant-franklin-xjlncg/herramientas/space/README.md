---
title: LeWelder
emoji: 🔥
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# LeWelder · simulador de la demo

Simulador de la demo de LeWelder (equipo Robotalde, Hackathon LeRobot Bilbao II): el robot SO-101 (Chispas) en 3D
moviéndose en tiempo real con la física de MuJoCo, la tablet arcade v2 y el juez soldando con el ratón.

- `/`: vista combinada (mesa 3D + tablet + panel del juez), pensada para 1920×1080.
- `/sim`: la mesa 3D con el panel del juez. `/tablet`: la tablet sola.
- `/?guion=jurado`: la secuencia del pitch de principio a fin, sola.

**Cada pestaña tiene su propia partida** (física, robot y puntuación propios; `?partida=ID` en la URL). Para ver la
tablet en otro dispositivo con la misma partida, abre el enlace `/tablet?partida=ID` que sale en la mesa. Como mucho
6 partidas a la vez (`LEWELDER_MAX_PARTIDAS`); con el aforo lleno, las pestañas nuevas entran en una partida
compartida y la mesa lo avisa. Las partidas sin nadie conectado se cierran a los 10 minutos. El ranking del día es
común a todas (se pierde al reiniciar el Space). Uso y controles: `docs/simulador.md` del repositorio.

## Montar el repo del Space

Desde la raíz del repositorio de LeWelder, en una copia del repo del Space:

```bash
cp herramientas/space/Dockerfile herramientas/space/README.md <space>/
mkdir -p <space>/herramientas/space <space>/assets <space>/hardware/v2/cad
cp herramientas/space/requirements-space.txt <space>/herramientas/space/
cp -r lewelder sim web <space>/
cp -r assets/so101 <space>/assets/
cp -r hardware/v2/cad/stl <space>/hardware/v2/cad/
```

Opcional: la variable secreta `ANTHROPIC_API_KEY` del Space activa el LLM para las órdenes raras (si no, la voz se
interpreta solo por reglas, que bastan para el vocabulario).
