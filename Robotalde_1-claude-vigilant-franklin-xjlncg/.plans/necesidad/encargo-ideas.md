# Encargo común para generar ideas concretas (18-11-2026)

## Restricciones duras
- Hackathon LeRobot Bilbao II, 20-22 nov 2026, 48 h, equipo de 3 (dos de software/IA, uno de CAD, impresión 3D y electrónica).
- Dos SO-101 (guía + seguidor), pinza de 2 dedos, carga útil ~200-300 g, repetibilidad de pocos mm; una cámara fija + opcional cámara de muñeca; GTX 1660 local y GPU en la nube.
- Imitación: ACT o SmolVLA con 50-150 demostraciones teleoperadas, grabadas allí (no hay robot antes).
- Fiable: coger y dejar objetos gruesos (≥ 20 mm, < 300 g) con tolerancia de ±1 cm (embudos, imanes, alojamientos en V muy abiertos). NO: inserción de precisión, fuerza, roscar, piezas pequeñas, finas o metálicas lisas, líquidos, contacto con personas, deformables.
- Hay que imprimir todo en 1,5 días; maquetas honestas: el jurado tiene que entender en 5 s que es la versión pequeña de algo real.
- Software reutilizable ya hecho: voz → LLM → orden cerrada, tablet con estética arcade, personaje con voz, ESP32 con sensores, ArUco y visión estéreo, flujo de LeRobot.

## Lo que pide el jurado (supuesto)
Necesidad real con impacto (cifra con fuente y una persona concreta), dificultad técnica, que funcione en vivo (30 %), uso VISIBLE de un VLA: una sola red que hace cosas distintas según la frase (mejor si la frase cambia un CRITERIO, no solo un objeto), momento memorable, el juez participa.

## Ya investigado (no repetir tal cual, pero se puede mejorar o combinar)
B triaje de baterías en reciclaje · E kits de montaje por variante · F fin de línea buenas/malas/retrabajo por voz · D carga de máquina multirreferencia · G estuche mixto de conservas · asistencia a personas · Relevo (repuestos en máquina, descartado por irreal) · LeWelder (soldadura, aparcado). Detalle en `.plans/necesidad/diagnostico.md`.

## Formato de cada ficha (obligatorio)
### Nombre · frase de 1 línea
- **Persona y dolor:** quién (puesto concreto), dolor cuantificado con fuente (URL) o marcado [sin fuente].
- **Lo real:** qué se hace hoy en planta y quién lo haría a escala real (empresa/sector, caso existente si lo hay).
- **La demo en mesa:** objetos (tamaño, nº), maqueta, qué hace el juez, final que se ve.
- **Órdenes del VLA (3-4 frases):** y qué cambia entre ellas (objeto, criterio, destino, cantidad).
- **Por qué solo un VLA lo hace bien:** frente a un cobot programado o visión clásica.
- **Fiabilidad:** el gesto más difícil y su tolerancia; plan B con ACT.
- **Coste de preparación:** piezas a imprimir, electrónica, episodios.
- **Puntos débiles honestos.**
- **Nota 1-5:** necesidad, VLA visible, fiabilidad, momento, frescura.
