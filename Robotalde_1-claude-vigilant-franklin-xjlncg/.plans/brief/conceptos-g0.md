# Conceptos del generador 0

## G0 · Aprendiz · «Faltan aprendices en los talleres. Hemos entrenado uno.»

1. **Usuario real y su trabajo.** El técnico de banco: quien repara o monta electrónica y aparatos pequeños en un
   taller de reparación, un laboratorio de FP o su casa. Trabaja con las dos manos ocupadas (sujeta la pieza y la
   herramienta) y pierde el hilo cada vez que suelta todo para buscar algo. En los oficios, eso lo hacía el
   aprendiz: acercar, sujetar, recoger. Hoy no hay aprendices (relevo generacional en Euskadi; cifras en
   `.plans/necesidad/investigacion-mantenimiento-euskadi.md`, por verificar).
2. **Reparto.** La persona hace el trabajo fino (desmontar, atornillar, montar). El robot le acerca lo que pide a la
   «zona de mano», se lo guarda en orden y recoge el banco al terminar. Cuando el robot falla, el maestro coge el
   brazo guía y le enseña: esa corrección se graba y cuenta en un marcador de autonomía.
3. **Referencia de physical AI real.** Ultra y Tutor (kits por pedido con una persona al lado; se mide el % de
   autonomía por turno), Medra (órdenes habladas en laboratorio), y MSN como precedente de valor en el banco.
4. **Escena tal cual.** Banco de 60 × 40 cm con tapete de corte. Cinco objetos reales de banco, gruesos: un
   destornillador de mango de Ø 22-28 mm, unos alicates de corte pequeños, un bote de flux o pegamento de Ø 25-30 mm,
   un carrete pequeño de estaño (Ø 40 mm) y un vaso de piezas (Ø 50 mm). Una bandeja «zona de mano» junto a la
   persona y un panel de sombras impreso con alojamientos en V para devolver cada cosa. Cámara fija cenital-diagonal
   y cámara de muñeca.
5. **Órdenes del VLA.** Nivel mínimo: `Hand over the screwdriver` y `Hand over the parts cup` (cambia el objeto, que
   es distinto a la vista y está donde el juez lo deje). Extra: `Hand over the cutters`, `Put the tools back`.
   El LLM compone: «voy a cambiar la batería» → vaso + destornillador. Un script no vale porque los objetos no están
   en posiciones fijas y la orden la elige el juez.
6. **Guion de 3 minutos.** (0:00) El juez se sienta a hacer un trabajo real corto: abrir un aparato y cambiarle una
   pieza. (0:20) Pide con sus palabras; el robot le acerca la herramienta. (1:00) El juez mueve los objetos a mano
   y vuelve a pedir: el robot los encuentra. (1:40) Fallo planificado o real: el maestro lo corrige con el brazo
   guía; el marcador pasa a «autónomo 5 de 6» y el personaje dice «apuntado, maestro». (2:20) «Recoge»: el robot
   devuelve las herramientas a su sombra. (2:50) El aparato funciona.
7. **Escalera.** N1: una orden de acercar con ACT o SmolVLA. N2: dos o tres objetos por voz con SmolVLA + marcador.
   N3: recoger el banco y cambio de orden a mitad con `/subtask`.
8. **Fiabilidad.** Gesto más difícil: coger un mango cilíndrico tumbado (±1 cm; se ayuda con apoyos impresos que lo
   levantan 1 cm). Dejar en bandeja: tolerancia de centímetros. Plan B: un ACT por objeto. Si falla, el rescate
   humano es parte del relato.
9. **Preparación del jueves.** ~6 h de impresión (bandeja, panel de sombras, apoyos, soportes de cámara); ESP32 con
   un botón de rescate y LED; se reutiliza voz → LLM, tablet y personaje.
10. **Puntos débiles.** Acercar una herramienta a 30 cm puede parecer algo que la persona hace mejor sola; el
    dominio (banco de electrónica) es el de MSN; el trabajo real del juez hay que elegirlo bien.

**Ajuste tras conocer la rúbrica de Robotekin (5 de 5 sin tocar):** la tarea completa declarada es «el juez pide una
herramienta de las del banco, colocada donde él quiera, y el robot la deja en la zona de mano» (≤ 30 s), repetida 5
veces con herramientas distintas; la zona de mano la vacía el juez al cogerla, sin entrar en el brazo. La corrección
del maestro sale de la demo puntuada y pasa a la historia de datos: «el aprendiz falló aquí el sábado, el maestro lo
corrigió 20 veces y subió de X a Y sobre 10».
