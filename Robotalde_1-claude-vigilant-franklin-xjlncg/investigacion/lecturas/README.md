# Lecturas: aprendizaje de robots, ACT y VLA

Conocimiento extraído el 18-11-2026 de libros, artículos y documentación para el hackathon. Cada documento marca lo
que no se pudo verificar en la fuente.

| Documento | Fuentes | Para qué |
|---|---|---|
| [tutorial-robot-learning-hf.md](tutorial-robot-learning-hf.md) | *Robot Learning: A Tutorial* (Hugging Face, arXiv:2510.12403) | Base teórica: imitación, ACT, Diffusion Policy, VLA, inferencia asíncrona |
| [act-diffusion-imitacion.md](act-diffusion-imitacion.md) | ACT/ALOHA, Diffusion Policy, Tedrake, Osa y otros | ACT en detalle: hiperparámetros, datos, por qué falla y cómo entrenarlo |
| [smolvla.md](smolvla.md) | Artículo de SmolVLA, blogs y docs de LeRobot 0.7 | Nuestra política principal: datos, ajuste fino, inferencia |
| [panorama-vla.md](panorama-vla.md) | π0, π0.5 y cuatro surveys de VLA | Fortalezas y debilidades de los VLA; ideas para la demo |
| [guia-practica-lerobot.md](guia-practica-lerobot.md) | Documentación de LeRobot v0.7.0 y código | Paso a paso con el SO-101: calibrar, grabar, entrenar, desplegar, grabar sin teleoperar |

## Conclusiones que afectan al plan

1. **Datos:** la referencia oficial de SmolVLA es **50 episodios por tarea** (10 en cada una de 5 posiciones de
   partida); con 25 salió mal. ACT llegó al 80-96 % con 50 demostraciones. → Mejor 2 órdenes bien grabadas que 3 a medias.
2. **Recolector programado:** sus demostraciones son más fáciles de imitar (ACT: 86 % frente a 50 % en simulación),
   pero no enseñan a recuperarse. → Añadir desviaciones y correcciones a propósito (nunca durante el agarre), mezclar
   con teleoperación y hacer un "DAgger ligero" (grabar desde donde la política se desvía). Ejemplo oficial que graba
   sin guía: `examples/omx/record_grab.py`.
3. **Órdenes:** SmolVLA se preentrenó con frases cortas en inglés que empiezan por verbo. → Una frase inglesa fija por
   orden en el dataset ("Build a T joint"...), el LLM traduce la voz a ella, la misma en `--task`. El artículo no
   prueba órdenes que solo se distinguen por la frase con la misma escena (riesgo T / esquina).
4. **Entrenamiento:** ACT necesita entrenar mucho más allá de que la pérdida se estabilice y elegir el modelo probando
   en el robot; el trozo de acciones debería cubrir ~1 s (≈ 30 pasos a 30 fps). SmolVLA: batch 64 y 20 000 pasos
   (~4 h en A100; 3-6 h en L4 según la doc) y 10-16 GB de VRAM → **se entrena en la nube**; ACT cabe en la GTX 1660.
5. **Despliegue en LeRobot 0.7:** el antiguo `async_inference` está retirado. Opciones: `lerobot-rollout
   --inference.type=rtc` (misma máquina; SmolVLA ocupa ~2 GB en inferencia, cabe en la 1660, latencia sin medir) o
   `lerobot-policy-server` + `--inference.type=remote` (no se recupera solo si se corta). `--interactive=true` y
   `/subtask` cambian la orden sin recargar el modelo. → Revisar la tarea 7 del plan (`robot_remoto.py`).
6. **Precisión:** ninguna fuente demuestra ±5 mm repetibles siguiendo una trayectoria con imitación. → La soldadura
   del robot, con replay o programada. La precisión de la imitación sale del bucle visual: contraste, luz y cámara de
   muñeca.
7. **Demo del VLA:** enseñar varias órdenes distintas al mismo modelo cargado, mostrar en pantalla la orden canónica
   mientras actúa y que el LLM rechace las órdenes que no sabe hacer.
8. **Comprobar ya:** `torch.cuda.is_available()` en el portátil Windows, versión de LeRobot en la imagen de HF Jobs,
   lectura de temperatura de los motores (`sync_read("Present_Temperature")`, sin documentar).
