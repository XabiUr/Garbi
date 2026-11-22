# Consejo · voz pragmática

Elección: **Pañol recortado** (3 herramientas, solo "traer"; "devolver a su sombra" como escalón extra). Confianza 7/10.

**Razones:** (1) se imprime en 1,5 días sin electrónica crítica (panel, 3 herramientas con asa alta, bandeja), mientras
que Relevo depende de pogo pins e inserción con contacto eléctrico; (2) VLA visible y fiable: 3 objetos distintos
en la misma escena elegidos por frase, coger y dejar con tolerancia; (3) reutiliza voz → LLM, tablet arcade, personaje
y ArUco. ManoLibre: emotiva, pero con agua cerca de la cara el fallo cuesta más y la dificultad percibida es baja.

**Presupuesto:** 3 órdenes ("trae la llave inglesa / el destornillador / los alicates a la bandeja") × 50 = 150
episodios + 20-30 de recuperación; teleoperación ~25-30 s por episodio → ~3 h de reloj con relevos. Descarta el
recolector programado (sin robot hasta el viernes no se afina a tiempo). SmolVLA en L4 (3-6 h), dos ciclos: prueba
que entrena sola durante la noche del viernes y definitivo el sábado. Se programa: LLM trabajo → kit, selector con
comprobación por ArUco y reintento, pantallas de la tablet, medición de aciertos. Miércoles-jueves: herramientas
simplificadas (sección ≥ 15 mm, colores distintos), panel con alojamientos en embudo, bandeja en V con ArUco,
soporte de cámara; LED bajo cada sombra opcional.

**Horario:** viernes 17-21 montaje, calibración, práctica, 50 episodios de A y entrenamiento rápido que corre solo
· sábado 9-12 probar y grabar B y C; 12:30 SmolVLA con las 3; mientras, integración y ACT por herramienta de red;
18-20 evaluación 10 intentos por orden · domingo 9-11 ensayar 3 veces sin tocar código.

**Mínimo sábado 20:00:** SmolVLA trae ≥ 2 de 3 herramientas a ≥ 70 % por voz, con reintento. Plan B: un ACT por
herramienta elegido por el LLM. Plan C: una herramienta en vivo y el resto en vídeo con la tasa de aciertos.

**Guion:** gancho ("en un taller se pierde una hora al día buscando herramientas") → el juez dice el trabajo → el LLM
muestra el kit → el robot trae una a una (verde por ArUco) → el juez quita una y el personaje la reclama, el robot la
vuelve a traer → un segundo juez pide otro trabajo con el mismo modelo → diapositiva de evidencia → cierre (talleres,
almacenes, FP).

Riesgo real: que "pasar herramientas" parezca fácil; se compensa con el LLM que razona, la recuperación y los números.
