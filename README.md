# Garbi · Hackathon LeRobot Bilbao II

Brazo SO-101 con boquilla de aspiración que limpia el serrín al taladrar.

- `plana/` — **el supervisor** (lo que funciona en el robot): detección del taladro (morado), aproximación con
  zonas o ACT, detección de la tabla de madera (`madera.py`) y barrido de la tabla (B) y del tapete (T)
  (`barrido.py`, modo rejilla). Arranque: `plana/arrancar.command` (doble clic) o `plana/supervisor_act.sh`.
- `Robotalde_1-claude-vigilant-franklin-xjlncg/` — el proyecto LeWelder/Garbi del equipo (producto, app web,
  simulador, hardware).

Calibraciones del barrido (independientes del taladro): `plana/calibrar_mesa.py --n-u 5 --n-v 3` y
`plana/grabar_posturas_mesa.py --real --a-mano`. Ajustes en `plana/config.json` → `"barrido"`.
