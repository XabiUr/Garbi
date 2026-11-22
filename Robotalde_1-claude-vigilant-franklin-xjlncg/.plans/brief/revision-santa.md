# Registro de la revisión `santa-method` del Brief (18-11-2026, noche)

Dos revisores independientes por ronda, con la misma rúbrica de seis criterios: exactitud y marcas, coherencia
interna, fidelidad a la versión 4, honestidad, accionable el jueves sin robot y hechos de LeRobot. Tope: cinco rondas.

| Ronda | Versión | Veredicto (B / C) | Críticos | Qué se corrigió |
|---|---|---|---|---|
| 1 | 4.0 | FAIL / FAIL | 10 | Alcance del técnico exagerado, U7 maquillado, episodios mal sumados, `Put it away.` sin entrenar, comparativa y medida que no cabían, viernes fuera de la agenda oficial, electrónica recortada que volvía, falta de contactos y umbrales |
| 2 | 4.1 | FAIL / FAIL | 4 + 7 | El jueves no hay robot; ensayos fuera de horario; medida bajada a 3 + 3 sin declarar; serie de 10 que no cabía; puertas del equipo rojo cambiadas; atribución de rechazos sin fuente |
| 3 | 4.2 | FAIL / FAIL | 4 + 4 | Plan sin noche solapado; ciclo 2 sin serie que lo midiera; puerta de la comparativa en la escala equivocada; atribución de rechazos |
| 4 | 4.3 | FAIL / FAIL | 6 + 5 | Puertas C y D contradictorias; cambios en las puertas sin declarar; puente y grabación a la vez; tanda 1 con dos horarios; ACT del ciclo 2 que nadie medía |
| 5 | 4.4 | FAIL / FAIL | 2 + 2 | Dos horas mal copiadas en el riesgo 1; umbral «salidas de manos» reescrito como «viajes al almacén»; cambio 2 de la versión 4 sin declarar |

En las rondas 4 y 5 los dos revisores aprobaron exactitud, honestidad, accionable y LeRobot; los fallos que quedaban
eran de calendario y de declaración de cambios. **Las correcciones de la ronda 5 (versión 4.5) no se han vuelto a
revisar** por el tope de cinco rondas: se escalan al usuario.

## Sugerencias no aplicadas (para la spec y el plan)

1. Tarea declarada: la caja se graba a 0° y ±30°; conviene declarar «con la caja a ±30°» o meter el giro en la puerta
   del domingo.
2. Puerta de la comparativa: falta el caso de los dos objetos por debajo de 5/10; «ninguna serie supera 1/5» es
   ambiguo en series de 10 (proponen «ninguna pasa del 20 %»).
3. Si el ciclo 2 llega tarde a las 19:20: usar el ciclo 1 y recortar la comparativa.
4. Margen de 15-20 min entre «modelo listo» y la prueba de la frase en el plan sin noche.
5. Tiempos de entrenamiento de los ACT en HF Jobs (`t4-small`) sin marcar como [est.].
6. La caja de 30 mm de ancho no admite el SO-DIMM dentro: iría lastrada sin módulo.
7. La disposición alternativa de mesa de 60 cm se sale del tablero de 530 × 600: Andoni debe acotar el segundo juego
   de taladros.
8. Andoni acumula demasiado el jueves (modelar, imprimir, visitas, compras, tablero): repartir compras o visitas.
9. Agarre de la caja: el especialista técnico dice «por el lado largo» y el de hardware «por el lado de 40»; unificar
   en `grabar.py` y en el protocolo.
10. Medida con y sin robot: 90 min en el Brief frente a 30 min del especialista; fijar la reserva real tras el jueves.
11. El alcance «solo estirándose» debilita «lo cojo yo en 3 s deja de ser verdad física» de la versión 4; declararlo
    como matiz.
12. Marcar en el resumen que los «20 puntos de datos» vienen de la rúbrica de Robotekin, de segunda mano.
