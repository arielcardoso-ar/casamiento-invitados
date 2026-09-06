#!/usr/bin/env python3
"""
Prepara las fotos de las polaroids de la invitación para la web.

Las fotos que salen del celular pesan 1-3 MB cada una: servidas tal cual, el
invitado que abre la invitación con 4G en la calle espera varios segundos antes
de ver nada. Este script genera dos anchos por foto (240 px y 480 px) para que
el `srcset` del template deje que cada teléfono baje sólo lo que necesita.
Los anchos están calculados para las polaroids del fondo, que nunca pasan
de 146 px: 240 px cubre una pantalla retina y 480 px una de 3x.

    cd scripts && ../.venv/bin/python preparar_fotos.py ~/Downloads/foto1.jpg ~/Downloads/foto2.jpg

Escribe `static/img/foto-1-240.jpg`, `foto-1-480.jpg`, `foto-2-…` y así.
Después hay que declararlas en `POLAROIDS`, en `config.py`.
"""

import os
import sys

from PIL import Image, ImageOps

# Las fotos de iPhone vienen en HEIC y Pillow no las abre por su cuenta.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

ANCHOS = (240, 480)
CALIDAD = 82

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DESTINO = os.path.join(RAIZ, 'static', 'img')


def preparar(origen, indice):
    img = Image.open(origen)
    # Sin esto, una foto sacada en vertical con el celular sale acostada: el
    # visor respeta el EXIF, el navegador no.
    img = ImageOps.exif_transpose(img).convert('RGB')

    generados = []
    for ancho in ANCHOS:
        # Encaja dentro de un cuadrado, no sólo por ancho: la polaroid recorta
        # un cuadrado, así que de una foto vertical bajar 600 px de ancho sería
        # traer el triple de píxeles de los que se van a ver.
        copia = img.copy()
        copia.thumbnail((ancho, ancho), Image.LANCZOS)

        nombre = f'foto-{indice}-{ancho}.jpg'
        ruta = os.path.join(DESTINO, nombre)
        copia.save(ruta, 'JPEG', quality=CALIDAD, optimize=True, progressive=True)
        generados.append((nombre, os.path.getsize(ruta), copia.size))

    return img.size, generados


def main(origenes):
    if not origenes:
        print(__doc__)
        return 1

    os.makedirs(DESTINO, exist_ok=True)

    for indice, origen in enumerate(origenes, 1):
        origen = os.path.expanduser(origen)
        if not os.path.exists(origen):
            print(f'✗ no existe: {origen}')
            return 1

        tamanio, generados = preparar(origen, indice)
        original = os.path.getsize(origen)
        print(f'{os.path.basename(origen)}  {tamanio[0]}×{tamanio[1]}  {original/1024:.0f} KB')
        for nombre, peso, (w, h) in generados:
            print(f'   → static/img/{nombre}  {w}×{h}  {peso/1024:.0f} KB')

    print(f'\nListo. Declaralas en POLAROIDS, en config.py.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
