# Garbi · Arduino de la aspiradora

Un relé en paralelo con el botón de la aspiradora. La aspiradora se enciende siempre que Garbi aspira: al acompañar
al taladro, al limpiar el agujero y en la pasada final.

**Funcionamiento:**
- El PC manda por USB `1` o `0` cada 200 ms; lo hace `garbi/real.py` (`SenalAspiradora`).
- Si pasa 1 s sin mensajes, el Arduino la apaga solo.

## Material

- Arduino Uno o Nano, con su cable USB al PC (siempre conectado; alimenta el Arduino y el relé).
- **Módulo de relé de 1 canal a 5 V**, con optoacoplador o transistor y diodo ya montados (el típico azul «SRD-05VDC»).
  No uses un relé suelto sin transistor ni diodo.
- 3 cables dupont hembra-macho y 2 cables finos para el botón; soldador y termorretráctil (o cinta).
- Polímetro.

## Paso 1 · Qué botón tiene la aspiradora (con ella DESENCHUFADA o sin batería)

Abre la carcasa y localiza las dos patas del botón. Polímetro en continuidad:

| Al pulsar y soltar… | Tipo | Modo del firmware |
|---|---|---|
| Hay continuidad mientras pulsas y desaparece al soltar; la aspiradora se enciende con un toque y se apaga con otro | Pulsador de toque | `MODO_PULSADOR` |
| Se queda con continuidad (clic) hasta volver a pulsar | Interruptor | `MODO_MANTENER` |

**Mira también qué pasa por el botón:**
- **Aspiradora con placa electrónica** (la mayoría de las de batería modernas): el botón solo lleva una señal de poca
  corriente. Cualquier relé vale.
- **El botón corta directamente el motor:**
  - en una de batería, eso son muchos amperios en continua, y el relé del módulo (10 A a 30 V DC) puede quedarse
    corto;
  - en una de enchufe, el botón está a 230 V.

  En los dos casos, lee «Seguridad» antes de seguir.

## Paso 2 · Conexión

```
 PC ──USB── Arduino                 Módulo de relé                    Aspiradora
            5V  ─────────────────── VCC
            GND ─────────────────── GND
            D7  ─────────────────── IN
                                    COM ───────────────── pata 1 del botón
                                    NO  ───────────────── pata 2 del botón
                                    (NC sin conectar)
```

- **COM y NO van en paralelo con el botón:** suelda un cable a cada pata y no quites el botón, así la aspiradora sigue
  funcionando a mano.
- **Con `MODO_MANTENER`,** deja el interruptor de la aspiradora en **OFF**: el relé hace de interruptor.
- **Saca los cables por un agujero de la carcasa** y sujétalos con una brida para que un tirón no arranque las
  soldaduras.

## Paso 3 · Programar

1. Abre `garbi_aspiradora.ino` en el IDE de Arduino.
2. En la línea `#define MODO`, elige `MODO_MANTENER` o `MODO_PULSADOR` (paso 1).
3. Placa Uno o Nano (en los Nano chinos: «ATmega328P (Old Bootloader)»), puerto y Subir.
4. Monitor Serie a 115200 con «Nueva línea»:
   - escribe `1`: el relé hace clic y se enciende el LED de la placa;
   - escribe `0`: se apaga;
   - si no escribes nada en 1 s, se apaga solo.
5. **Si el relé funciona al revés** (activo cuando debería estar en reposo), cambia `RELE_ACTIVO_BAJO` a `false`.

## Paso 4 · Probar con la aspiradora y el PC

Cierra el Monitor Serie (el puerto solo lo puede usar un programa) y ejecuta:

```bash
python herramientas/probar_aspiradora.py COM5
```

En Linux, el puerto es `/dev/ttyACM0` o `/dev/ttyUSB0`.

**Qué debe pasar:**
1. La aspiradora se enciende 3 s y se apaga.
2. Se enciende y se apaga sola ~1 s después de cortar la señal.

Con Garbi:

```bash
python -m garbi.correr --real --puerto <robot> --aspiradora COM5
```

## Modo pulsador: precauciones

- El Arduino **no sabe** si la aspiradora está encendida: lo deduce de los toques que ha dado. Arranca siempre con la
  aspiradora **apagada**.
- Si alguien la toca a mano y se desincroniza, escribe `S` en el Monitor Serie: cambia el estado que el Arduino cree
  que tiene, sin dar toque.
- Si la aspiradora necesita un toque más largo o más corto, ajusta `PULSO_MS`; el valor por defecto es 250 ms.

## Seguridad

- Trabaja siempre con la aspiradora **desenchufada o sin batería**.
- Si el botón está a 230 V (aspiradora de enchufe sin placa electrónica):
  - el módulo aguanta 250 V y 10 A, pero sus pistas de 230 V quedan al aire;
  - mételo en una caja de plástico cerrada, con los cables de 230 V bien aislados y sujetos;
  - mejor aún, **no abras la aspiradora**: deja su interruptor encendido y usa un enchufe inteligente controlable
    desde el PC.
- Si el botón corta directamente un motor de batería (muchos amperios en continua), usa un relé de automoción de 12 V
  y 30-40 A gobernado por el módulo, o un MOSFET de potencia. Pregunta antes de improvisar.
- El latido apaga la aspiradora si el PC se cuelga o se suelta el USB. Aun así, la aspiradora debe tener a mano su
  propio botón o enchufe.
