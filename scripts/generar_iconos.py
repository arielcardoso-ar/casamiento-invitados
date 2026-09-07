#!/usr/bin/env python3
"""
Genera los íconos para "agregar a pantalla de inicio".

    cd scripts && ../.venv/bin/python generar_iconos.py

El maskable lleva más aire alrededor: Android recorta el ícono con la forma que
tenga el launcher (círculo, gota, cuadrado redondeado) y sólo garantiza que se
vea el 80% central. Sin ese margen, el monograma queda mordido.
"""

import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DESTINO = os.path.join(RAIZ, 'static', 'img')

CREMA = (253, 252, 249)
VERDE = (59, 76, 51)
SALVIA = (149, 176, 131)
ROSA = (226, 156, 160)


def _fuente(tamanio):
    for nombre in ('SnellRoundhand.ttc', 'Zapfino.ttf', 'Georgia Italic.ttf', 'Georgia.ttf'):
        for carpeta in ('/System/Library/Fonts', '/System/Library/Fonts/Supplemental',
                        '/Library/Fonts'):
            ruta = os.path.join(carpeta, nombre)
            if os.path.exists(ruta):
                try:
                    return ImageFont.truetype(ruta, tamanio)
                except OSError:
                    continue
    return ImageFont.load_default()


def dibujar(lado, margen):
    """`margen` es la fracción libre en cada borde (0.10 normal, 0.20 maskable)."""
    img = Image.new('RGB', (lado, lado), CREMA)
    d = ImageDraw.Draw(img)

    util = lado * (1 - 2 * margen)
    x0 = y0 = lado * margen
    x1 = y1 = x0 + util

    # Aro exterior salvia y aro interior rosa: el mismo doble filete del hero.
    d.ellipse([x0, y0, x1, y1], outline=SALVIA, width=max(2, int(lado * 0.016)))
    aire = util * 0.055
    d.ellipse([x0 + aire, y0 + aire, x1 - aire, y1 - aire],
              outline=ROSA, width=max(1, int(lado * 0.008)))

    # Monograma centrado sobre el alto real del glifo, no sobre la caja de la
    # fuente: si no, las mayúsculas caligráficas quedan visiblemente bajas.
    texto = 'K&A'
    fuente = _fuente(int(util * 0.32))
    izq, arriba, der, abajo = d.textbbox((0, 0), texto, font=fuente)
    d.text((lado / 2 - (der - izq) / 2 - izq,
            lado / 2 - (abajo - arriba) / 2 - arriba),
           texto, font=fuente, fill=VERDE)
    return img


def main():
    os.makedirs(DESTINO, exist_ok=True)
    for nombre, lado, margen in (('icono-192.png', 192, 0.10),
                                 ('icono-512.png', 512, 0.10),
                                 ('icono-512-maskable.png', 512, 0.20)):
        ruta = os.path.join(DESTINO, nombre)
        dibujar(lado, margen).save(ruta, 'PNG', optimize=True)
        print(f'  → static/img/{nombre}  ({os.path.getsize(ruta) / 1024:.0f} KB)')


if __name__ == '__main__':
    main()
