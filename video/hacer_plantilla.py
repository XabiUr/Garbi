#!/usr/bin/env python3
"""
hacer_plantilla.py - Genera el guion y la plantilla del vídeo de Garbi a partir de la lista de ESCENAS.

Salida (en esta carpeta, plana/video/):
    guion.md              el guion: escenas, duración, qué grabar y el texto de cada una
    rotulos/NN_*.png      los rótulos sueltos (1920×1080) para usarlos en iMovie / Final Cut
    plantilla_garbi.mp4   el vídeo ya montado con rótulos y HUECOS marcados donde van tus grabaciones

Para cambiar el vídeo: edita ESCENAS y vuelve a ejecutar:
    python video/hacer_plantilla.py
"""

import os
import textwrap

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
ANCHO, ALTO, FPS = 1920, 1080, 30
FUENTE = "/System/Library/Fonts/HelveticaNeue.ttc"
MARCA = (13, 148, 136)        # verde azulado de la app
OSCURO = (15, 23, 42)
CLARO = (241, 245, 249)
AMBAR = (245, 158, 11)

# tipo: "rotulo" (lo genero yo) o "hueco" (lo grabas tú). fuente: de dónde sale la grabación.
ESCENAS = [
    # Mensaje: el valor de no tener que parar a quitar la biruta.
    {"tipo": "rotulo", "seg": 4, "titulo": "Garbi", "texto": "Tú taladras. Garbi limpia.",
     "pie": "Hackathon LeRobot Bilbao II · Robotalde"},
    {"tipo": "hueco", "seg": 8, "titulo": "Taladrar = parar a limpiar",
     "graba": "Con el móvil: alguien taladra, para, sopla o barre la biruta con la mano, vuelve a marcar y sigue. Que se note la pausa.",
     "fuente": "Móvil", "voz": "Cada agujero deja biruta. Y cada vez hay que parar a quitarla para ver la marca y seguir."},
    {"tipo": "rotulo", "seg": 4, "titulo": "¿Y si no tuvieras que parar?",
     "texto": "Un brazo que recoge la biruta mientras trabajas"},
    {"tipo": "hueco", "seg": 15, "titulo": "Tú sigues taladrando",
     "graba": "Cámaras juntas (o móvil): mientras se taladra, el brazo se acerca solo a la broca y se queda junto a ella aspirando.",
     "fuente": "grabar_camaras.py → *_juntas.mp4 + móvil", "voz": "Garbi ve el taladro, acerca la boquilla a la broca y recoge la biruta mientras tú sigues.",
     "clip": "clips/entrenamiento.mp4"},   # ya relleno con episodios reales del entrenamiento (clip_entrenamiento.py)
    {"tipo": "hueco", "seg": 12, "titulo": "Al terminar, limpia la pieza",
     "graba": "Web o cámara superior: detecta la tabla (rectángulo verde) y la barre en zigzag.",
     "fuente": "grabar_camaras.py → *_superior.mp4 (o pantalla)", "voz": "Al terminar, limpia la pieza, esté donde esté."},
    {"tipo": "hueco", "seg": 10, "titulo": "Y deja el puesto limpio",
     "graba": "Sin la tabla: barrido completo del tapete (puede ir acelerado x2 en el montaje).",
     "fuente": "grabar_camaras.py → *_superior.mp4 o móvil", "voz": "Y deja el puesto de trabajo limpio."},
    {"tipo": "rotulo", "seg": 7, "titulo": "Sin pausas para limpiar",
     "texto": "Más tiempo taladrando · Puesto limpio · Menos polvo · Marca siempre visible",
     "pie": "El valor: nadie tiene que parar a quitar la biruta"},
    {"tipo": "hueco", "seg": 10, "titulo": "Seguro: si hay una mano, para",
     "graba": "Durante una limpieza, meter la mano: el brazo se queda QUIETO; al quitarla, vuelve a reposo.",
     "fuente": "Móvil + *_superior.mp4", "voz": "Si ve una mano o el taladro, se detiene y espera a que la zona quede libre.",
     "clip": "clips/seguridad.mp4"},   # ya relleno: IMG_0274.MOV recortado con rótulos (clip_seguridad.py)
    {"tipo": "hueco", "seg": 10, "titulo": "Fácil: un clic desde la app",
     "graba": "Pantalla de la web: Encender (con la comprobación), «Limpiar tabla», estado y cámaras en directo.",
     "fuente": "Pantalla (⌘⇧5)", "voz": "Se maneja con un clic desde la app: encender, limpiar la pieza o el tapete."},
    {"tipo": "hueco", "seg": 5, "titulo": "Paro de emergencia",
     "graba": "Pulsar la seta (o ESPACIO): el brazo se para al instante.",
     "fuente": "Móvil", "voz": "Y siempre con paro de emergencia."},
    {"tipo": "rotulo", "seg": 5, "titulo": "Cómo funciona",
     "texto": "SO-101 · LeRobot · ACT · OpenCV · MediaPipe · App web",
     "pie": "Aspiradora: en integración (la app ya indica cuándo aspirar)"},
    {"tipo": "rotulo", "seg": 4, "titulo": "Garbi", "texto": "Tú taladras. Garbi limpia.",
     "pie": "github.com/XabiUr/Garbi  ·  huggingface.co/datasets/Xaflas/garbi_V1.0.0"},
]


def fuente(tam, negrita=False):
    try:
        return ImageFont.truetype(FUENTE, tam, index=1 if negrita else 0)
    except OSError:
        return ImageFont.load_default()


def centrado(d, y, texto, f, color, margen=160):
    # si no cabe, reduce la letra hasta que quepa en el ancho
    while d.textlength(texto, font=f) > ANCHO - 2 * margen and getattr(f, "size", 0) > 20:
        f = f.font_variant(size=f.size - 2)
    w = d.textlength(texto, font=f)
    d.text(((ANCHO - w) / 2, y), texto, font=f, fill=color)


def dibujar_rotulo(e) -> Image.Image:
    im = Image.new("RGB", (ANCHO, ALTO), OSCURO)
    d = ImageDraw.Draw(im)
    d.rectangle([0, ALTO - 14, ANCHO, ALTO], fill=MARCA)
    centrado(d, 380, e["titulo"], fuente(130, True), (255, 255, 255))
    if e.get("texto"):
        centrado(d, 560, e["texto"], fuente(56), (148, 230, 220))
    if e.get("pie"):
        centrado(d, 900, e["pie"], fuente(34), (148, 163, 184))
    return im


def dibujar_hueco(e, n) -> Image.Image:
    im = Image.new("RGB", (ANCHO, ALTO), (30, 41, 59))
    d = ImageDraw.Draw(im)
    # marco discontinuo
    m = 70
    for x in range(m, ANCHO - m, 40):
        d.line([x, m, x + 22, m], fill=AMBAR, width=6)
        d.line([x, ALTO - m, x + 22, ALTO - m], fill=AMBAR, width=6)
    for y in range(m, ALTO - m, 40):
        d.line([m, y, m, y + 22], fill=AMBAR, width=6)
        d.line([ANCHO - m, y, ANCHO - m, y + 22], fill=AMBAR, width=6)
    centrado(d, 150, f"HUECO {n} · AQUÍ VA TU VÍDEO · {e['seg']} s", fuente(52, True), AMBAR)
    centrado(d, 260, e["titulo"], fuente(96, True), (255, 255, 255))
    y = 430
    for linea in textwrap.wrap(e["graba"], 62):
        centrado(d, y, linea, fuente(46), CLARO)
        y += 62
    centrado(d, y + 40, f"Fuente: {e['fuente']}", fuente(38), (148, 230, 220))
    if e.get("voz"):
        centrado(d, ALTO - 210, f"Texto / voz: «{e['voz']}»", fuente(32), (148, 163, 184))
    return im


def main():
    os.makedirs(os.path.join(AQUI, "rotulos"), exist_ok=True)
    salida = os.path.join(AQUI, "plantilla_garbi.mp4")
    vid = cv2.VideoWriter(salida, cv2.VideoWriter_fourcc(*"avc1"), FPS, (ANCHO, ALTO))
    lineas = ["# Guion del vídeo de Garbi", "",
              "Generado por `video/hacer_plantilla.py` (edita ESCENAS ahí y vuelve a ejecutarlo).", "",
              "En `plantilla_garbi.mp4` los rótulos ya están hechos; cada **HUECO** es una pantalla marcada en ámbar",
              "que tienes que sustituir por tu grabación (misma duración, o la que quieras).", "",
              "| # | Tiempo | Escena | Qué es / qué grabar | De dónde sale | Texto o voz |",
              "|---|---|---|---|---|---|"]
    t, n_hueco = 0, 0
    for i, e in enumerate(ESCENAS, 1):
        clip = os.path.join(AQUI, e["clip"]) if e.get("clip") else None
        if clip and os.path.exists(clip):   # hueco ya relleno con un clip: se mete tal cual
            n_hueco += 1
            c = cv2.VideoCapture(clip)
            n_frames, primero = 0, None
            while True:
                ok, f = c.read()
                if not ok:
                    break
                f = cv2.resize(f, (ANCHO, ALTO))
                primero = f if primero is None else primero
                vid.write(f)
                n_frames += 1
            c.release()
            seg = round(n_frames / FPS)
            if primero is not None:
                cv2.imwrite(os.path.join(AQUI, "rotulos", f"{i:02d}_clip.png"), primero)
            lineas.append(f"| {i} | {t // 60}:{t % 60:02d}–{(t + seg) // 60}:{(t + seg) % 60:02d} | {e['titulo']} | "
                          f"**HUECO {n_hueco} · YA RELLENO** con `{e['clip']}`. "
                          f"Si grabas el robot en directo, puedes sustituirlo | {e['fuente']} | {e.get('voz', '')} |")
            t += seg
            continue
        if e["tipo"] == "hueco":
            n_hueco += 1
            im = dibujar_hueco(e, n_hueco)
            que, de, voz = f"**HUECO {n_hueco}** · {e['graba']}", e["fuente"], e.get("voz", "")
        else:
            im = dibujar_rotulo(e)
            que, de, voz = "Rótulo (hecho)", "—", " · ".join(x for x in (e.get("texto"), e.get("pie")) if x)
        nombre = f"{i:02d}_{'hueco' if e['tipo'] == 'hueco' else 'rotulo'}.png"
        im.save(os.path.join(AQUI, "rotulos", nombre))
        fotograma = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        for _ in range(int(e["seg"] * FPS)):
            vid.write(fotograma)
        lineas.append(f"| {i} | {t // 60}:{t % 60:02d}–{(t + e['seg']) // 60}:{(t + e['seg']) % 60:02d} | "
                      f"{e['titulo']} | {que} | {de} | {voz} |")
        t += e["seg"]
    vid.release()
    lineas += ["", f"**Duración total: {t // 60}:{t % 60:02d}**", "",
               "## Cómo grabar cada cosa", "",
               "- **Pantalla de la web**: ⌘⇧5 → «Grabar parte seleccionada» → ajusta el recuadro a la ventana del navegador.",
               "- **Cámaras del robot**: con el supervisor en marcha (desde la web), en otra Terminal:",
               "  `cd /Users/xabier/Desktop/Hackathon/Garbi/plana && python grabar_camaras.py`",
               "  → `video/grabaciones/AAAAMMDD_HHMMSS_{superior,muneca,juntas}.mp4` (Ctrl+C para parar).",
               "- **Planos generales**: con el móvil, en horizontal y fijo (mejor apoyado).",
               "", "## Montaje en el Mac (iMovie)", "",
               "1. Nuevo proyecto → importa `plantilla_garbi.mp4` y tus grabaciones.",
               "2. Arrastra la plantilla a la línea de tiempo.",
               "3. Cada HUECO es un tramo ámbar: ponle encima tu clip (o córtalo y sustitúyelo). Los rótulos sueltos están en `rotulos/` por si prefieres montarlo de cero.",
               "4. Añade música o voz en off con los textos de la tabla.",
               "5. Archivo → Compartir → Archivo (1080p).", ""]
    with open(os.path.join(AQUI, "guion.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"✓ {salida} ({t} s) · guion.md · rotulos/ ({len(ESCENAS)} PNG)")


if __name__ == "__main__":
    main()
