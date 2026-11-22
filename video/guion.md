# Guion del vídeo de Garbi

Generado por `video/hacer_plantilla.py` (edita ESCENAS ahí y vuelve a ejecutarlo).

En `plantilla_garbi.mp4` los rótulos ya están hechos; cada **HUECO** es una pantalla marcada en ámbar
que tienes que sustituir por tu grabación (misma duración, o la que quieras).

| # | Tiempo | Escena | Qué es / qué grabar | De dónde sale | Texto o voz |
|---|---|---|---|---|---|
| 1 | 0:00–0:04 | Garbi | Rótulo (hecho) | — | Tú taladras. Garbi limpia. · Hackathon LeRobot Bilbao II · Robotalde |
| 2 | 0:04–0:12 | Taladrar = parar a limpiar | **HUECO 1** · Con el móvil: alguien taladra, para, sopla o barre la biruta con la mano, vuelve a marcar y sigue. Que se note la pausa. | Móvil | Cada agujero deja biruta. Y cada vez hay que parar a quitarla para ver la marca y seguir. |
| 3 | 0:12–0:16 | ¿Y si no tuvieras que parar? | Rótulo (hecho) | — | Un brazo que recoge la biruta mientras trabajas |
| 4 | 0:16–0:29 | Tú sigues taladrando | **HUECO 2 · YA RELLENO** con `clips/entrenamiento.mp4`. Si grabas el robot en directo, puedes sustituirlo | grabar_camaras.py → *_juntas.mp4 + móvil | Garbi ve el taladro, acerca la boquilla a la broca y recoge la biruta mientras tú sigues. |
| 5 | 0:29–0:41 | Al terminar, limpia la pieza | **HUECO 3** · Web o cámara superior: detecta la tabla (rectángulo verde) y la barre en zigzag. | grabar_camaras.py → *_superior.mp4 (o pantalla) | Al terminar, limpia la pieza, esté donde esté. |
| 6 | 0:41–0:51 | Y deja el puesto limpio | **HUECO 4** · Sin la tabla: barrido completo del tapete (puede ir acelerado x2 en el montaje). | grabar_camaras.py → *_superior.mp4 o móvil | Y deja el puesto de trabajo limpio. |
| 7 | 0:51–0:58 | Sin pausas para limpiar | Rótulo (hecho) | — | Más tiempo taladrando · Puesto limpio · Menos polvo · Marca siempre visible · El valor: nadie tiene que parar a quitar la biruta |
| 8 | 0:58–1:10 | Seguro: si hay una mano, para | **HUECO 5 · YA RELLENO** con `clips/seguridad.mp4`. Si grabas el robot en directo, puedes sustituirlo | Móvil + *_superior.mp4 | Si ve una mano o el taladro, se detiene y espera a que la zona quede libre. |
| 9 | 1:10–1:20 | Fácil: un clic desde la app | **HUECO 6** · Pantalla de la web: Encender (con la comprobación), «Limpiar tabla», estado y cámaras en directo. | Pantalla (⌘⇧5) | Se maneja con un clic desde la app: encender, limpiar la pieza o el tapete. |
| 10 | 1:20–1:25 | Paro de emergencia | **HUECO 7** · Pulsar la seta (o ESPACIO): el brazo se para al instante. | Móvil | Y siempre con paro de emergencia. |
| 11 | 1:25–1:30 | Cómo funciona | Rótulo (hecho) | — | SO-101 · LeRobot · ACT · OpenCV · MediaPipe · App web · Aspiradora: en integración (la app ya indica cuándo aspirar) |
| 12 | 1:30–1:34 | Garbi | Rótulo (hecho) | — | Tú taladras. Garbi limpia. · github.com/XabiUr/SOS101-drill-and-clean |

**Duración total: 1:34**

## Cómo grabar cada cosa

- **Pantalla de la web**: ⌘⇧5 → «Grabar parte seleccionada» → ajusta el recuadro a la ventana del navegador.
- **Cámaras del robot**: con el supervisor en marcha (desde la web), en otra Terminal:
  `cd /Users/xabier/Desktop/Hackathon/Garbi/plana && python grabar_camaras.py`
  → `video/grabaciones/AAAAMMDD_HHMMSS_{superior,muneca,juntas}.mp4` (Ctrl+C para parar).
- **Planos generales**: con el móvil, en horizontal y fijo (mejor apoyado).

## Montaje en el Mac (iMovie)

1. Nuevo proyecto → importa `plantilla_garbi.mp4` y tus grabaciones.
2. Arrastra la plantilla a la línea de tiempo.
3. Cada HUECO es un tramo ámbar: ponle encima tu clip (o córtalo y sustitúyelo). Los rótulos sueltos están en `rotulos/` por si prefieres montarlo de cero.
4. Añade música o voz en off con los textos de la tabla.
5. Archivo → Compartir → Archivo (1080p).
