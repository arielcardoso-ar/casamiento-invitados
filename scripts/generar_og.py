#!/usr/bin/env python3
"""
Arma la imagen de previsualización que se ve al compartir el link.

Cuando alguien manda la invitación por WhatsApp, lo que decide si el otro la
abre es esa tarjetita con imagen. Sin `og:image` WhatsApp muestra un rectángulo
gris con la URL y parece spam.

    cd scripts && ../.venv/bin/python generar_og.py <foto.jpg>

Escribe static/img/og.jpg en 1200×630, que es la relación que esperan WhatsApp,
Facebook, Telegram e iMessage.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ANCHO, ALTO = 1200, 630
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SALIDA = os.path.join(RAIZ, 'static', 'img', 'og.jpg')

# La misma paleta del sitio.
VERDE = (59, 76, 51)
CREMA = (253, 252, 249)
ROSA = (226, 156, 160)


def _fuente(nombres, tamanio):
    """Primera fuente del sistema que exista, o la de Pillow si no hay ninguna."""
    for nombre in nombres:
        for carpeta in ('/System/Library/Fonts', '/System/Library/Fonts/Supplemental',
                        '/Library/Fonts'):
            ruta = os.path.join(carpeta, nombre)
            if os.path.exists(ruta):
                try:
                    return ImageFont.truetype(ruta, tamanio)
                except OSError:
                    continue
    return ImageFont.load_default()


def _centrar(draw, texto, fuente, y, color):
    izq, arriba, der, abajo = draw.textbbox((0, 0), texto, font=fuente)
    draw.text(((ANCHO - (der - izq)) / 2 - izq, y), texto, font=fuente, fill=color)
    return abajo - arriba


def generar(origen, novia='Kathy', novio='Ari', fecha='16 · ENERO · 2027',
            lugar='Basílica de Lourdes · Buenos Aires'):
    foto = ImageOps.exif_transpose(Image.open(origen)).convert('RGB')

    # Recorte a 1200×630 centrado un poco arriba, donde suelen estar las caras.
    fondo = ImageOps.fit(foto, (ANCHO, ALTO), Image.LANCZOS, centering=(0.5, 0.38))

    # Un velo claro, como el resto del sitio: la foto se ve, el texto se lee.
    velo = Image.new('RGB', (ANCHO, ALTO), CREMA)
    fondo = Image.blend(fondo, velo, 0.62)
    fondo = fondo.filter(ImageFilter.GaussianBlur(0.6))

    draw = ImageDraw.Draw(fondo)

    # Doble filete, el mismo marco de papelería del hero.
    draw.rectangle([28, 28, ANCHO - 29, ALTO - 29], outline=(150, 175, 140), width=2)
    draw.rectangle([40, 40, ANCHO - 41, ALTO - 41], outline=ROSA, width=1)

    script = _fuente(['SnellRoundhand.ttc', 'Zapfino.ttf', 'Georgia Italic.ttf',
                      'Georgia.ttf'], 128)
    chica = _fuente(['Optima.ttc', 'Palatino.ttc', 'Georgia.ttf'], 34)
    mini = _fuente(['Optima.ttc', 'Palatino.ttc', 'Georgia.ttf'], 27)

    _centrar(draw, 'NOS  CASAMOS', mini, 128, (97, 123, 80))
    _centrar(draw, f'{novia}  &  {novio}', script, 196, VERDE)
    _centrar(draw, fecha, chica, 396, (85, 96, 74))
    _centrar(draw, lugar, mini, 456, (120, 130, 108))

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    fondo.save(SALIDA, 'JPEG', quality=88, optimize=True, progressive=True)
    return SALIDA


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    ruta = generar(os.path.expanduser(sys.argv[1]))
    print(f'{ruta}  ({os.path.getsize(ruta) / 1024:.0f} KB)')
