# LeWelder · Robotalde · Hackathon LeRobot Bilbao II

Responde siempre en español.

## Al empezar una sesión

1. Lee [estado.md](estado.md): dice en qué fase estamos y cuál es el siguiente paso.
2. Lee la spec en [.plans/lewelder-spec.md](.plans/lewelder-spec.md).
3. La investigación de referencia está en `investigacion/`.

## En el portátil del hackathon (robot real)

**Primero lee [docs/CONTEXTO-LOCAL.md](docs/CONTEXTO-LOCAL.md)**: qué se ha construido, qué tiene el equipo en su PC
(dataset, ACT, detector morado, matriz 5×3) y cómo integrarlo. El producto final está en `garbi/producto/` y se
configura en `garbi/producto/garbi_producto.yaml`. Si el usuario trabaja con el robot real, usa además la skill
`/garbi-sitio` (acompañante paso a paso) y la guía [docs/garbi-guia-hackathon.md](docs/garbi-guia-hackathon.md).

## Flujo de trabajo (resumen del flujo del equipo)

Este proyecto es de tipo **hackathon**: todas las fases, a fondo.

0. Retomar: leer `estado.md`.
1. Resultado final: la demo ganadora y un ejemplo existente como base. **Hecha.**
2. Spec con la skill `/jmo-workflow:interview` → `.plans/lewelder-spec.md`. **En curso.**
3. Plan con `/ecc:plan .plans/lewelder-spec.md`, tareas independientes y un subagente por tarea (cada una en su
   worktree con git). Puerta: "sí" explícito del usuario.
4. Construir y verificar según el tipo de cada parte (código: TDD, revisión, verificación; hardware: CAD y
   comprobación contra la spec).
5. Al final: guion y prueba de la demo en vivo.

Reglas: una puerta por fase; no empezar una fase sin el entregable de la anterior; si se quiere saltar una fase o
una skill, decir cuál y por qué y esperar la aprobación del usuario. Si las skills no están disponibles en el entorno,
decirlo y proponer la alternativa más cercana. Al cerrar cada fase, informar en una línea:
`Fase N · skill invocada → entregable (ruta)`. Mantener `estado.md` al día.

## Convenciones

- Código en Python 3.12 con LeRobot 0.7. Nombres y comentarios en español.
- No subir datasets, modelos ni `.venv` al repositorio: los datasets y modelos van a Hugging Face.
- Commits con formato `tipo: descripción` (feat, fix, docs, chore...), sin líneas de atribución.
