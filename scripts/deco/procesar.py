"""Pasa los originales de mflux (raw/) a assets livianos para la invitación."""
import os
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

RAW = Path(os.environ.get('DECO_RAW', Path(__file__).parent / 'raw'))
OUT = Path(sys.argv[1])


def abrir(nombre):
    return np.asarray(Image.open(RAW / nombre).convert('RGB')).astype(np.float32) / 255


def acuarela_sin_fondo(rgb, piso=0.035):
    """Saca el papel blanco: alfa = cuánto se aparta del blanco, color sin premultiplicar.
    Así la acuarela queda transparente sobre cualquier fondo, como pintada encima."""
    a = 1 - rgb.min(axis=2)
    a = np.clip((a - piso) / (1 - piso), 0, 1)
    a = np.clip(a * 1.15, 0, 1)
    col = 1 - (1 - rgb) / np.maximum(a[..., None], 1e-3)
    col = np.clip(col, 0, 1)
    return np.dstack([col, a])


def recortar(img_rgba, margen=8):
    a = np.asarray(img_rgba)[..., 3]
    ys, xs = np.where(a > 8)
    box = (max(xs.min() - margen, 0), max(ys.min() - margen, 0),
           min(xs.max() + margen, a.shape[1]), min(ys.max() + margen, a.shape[0]))
    return img_rgba.crop(box)


def guardar(img, nombre, ancho=None, **kw):
    if ancho and img.width > ancho:
        img = img.resize((ancho, round(img.height * ancho / img.width)), Image.LANCZOS)
    p = OUT / nombre
    img.save(p, **kw)
    print(f'{nombre}: {img.size} {p.stat().st_size // 1024} KB')


def a_imagen(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8))


def textura(rgb, contraste, lado):
    """Grano neutro alrededor del blanco para usar con multiply y sin costuras."""
    g = rgb.mean(axis=2)
    base = np.asarray(a_imagen(g).filter(ImageFilter.GaussianBlur(40))).astype(np.float32) / 255
    det = g / np.maximum(base, 1e-3)              # sólo la fibra, sin manchas de luz
    t = 1 - np.clip((1 - det) * contraste, 0, 1)
    t = np.clip(t, 0, 1)
    # Sin costuras: se descartan los bordes (el desenfoque los altera) y se
    # espeja en 2x2; con un grano tan suave el espejo no se nota.
    h, w = t.shape
    t = t[h // 8: h - h // 8, w // 8: w - w // 8]
    t = np.vstack([np.hstack([t, t[:, ::-1]]), np.hstack([t[::-1], t[::-1, ::-1]])])
    t = t - t.mean() + 0.965                       # aclara: apenas tiñe al multiplicar
    img = a_imagen(t).convert('L').resize((lado, lado), Image.LANCZOS)
    return img


# Papel: grano de algodón para las secciones blancas.
guardar(textura(abrir('papel-11.png'), 1.3, 512), 'papel.jpg', quality=82)
# Lino salvia del sobre, también como grano neutro.
guardar(textura(abrir('sobre-13.png'), 3.0, 512), 'lino.jpg', quality=82)

# Lacre: se recorta en círculo con el borde irregular de la cera.
rgb = abrir('lacre-5.png')
sat = rgb.max(axis=2) - rgb.min(axis=2)
mask = a_imagen((sat > 0.07).astype(np.float32)).filter(ImageFilter.MedianFilter(5))
# Rellena huecos (brillos blancos dentro de la cera).
m = np.asarray(mask) > 127
from collections import deque
fuera = np.zeros_like(m)
q = deque([(0, 0)]); fuera[0, 0] = True
H, W = m.shape
while q:
    y, x = q.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < H and 0 <= nx < W and not fuera[ny, nx] and not m[ny, nx]:
            fuera[ny, nx] = True; q.append((ny, nx))
alfa = a_imagen((~fuera).astype(np.float32)).filter(ImageFilter.GaussianBlur(1.2))
lacre = Image.open(RAW / 'lacre-5.png').convert('RGB')
lacre.putalpha(alfa)
lacre = recortar(lacre, 2)
lado = max(lacre.size)
cuad = Image.new('RGBA', (lado, lado)); cuad.paste(lacre, ((lado - lacre.width) // 2, (lado - lacre.height) // 2))
guardar(cuad, 'lacre.webp', 240, quality=86, method=6)

# Acuarelas con transparencia.
for origen, destino, ancho, calidad in (('ramo-29.png', 'ramo.webp', 560, 72), ('ramo-3.png', 'ramo-2.webp', 560, 72),
                                        ('ramita-7.png', 'ramita.webp', 300, 78), ('banda-41.png', 'banda.webp', 960, 66),
                                        ('guirnalda-12.png', 'guirnalda.webp', 640, 76), ('guirnalda-44.png', 'guirnalda-2.webp', 480, 76),
                                        ('corona-9.png', 'corona.webp', 512, 88)):
    rgba = acuarela_sin_fondo(abrir(origen))
    if destino == 'banda.webp':
        rgba[..., 3] *= 0.55        # va detrás de texto: más aguada
    rgba = (rgba * 255).round().astype(np.uint8)
    img = recortar(Image.frombuffer('RGBA', rgba.shape[1::-1], rgba.tobytes()))
    guardar(img, destino, ancho, quality=calidad, method=6)
    # Versión para celular: el ramo se ve a 150 px y la banda a ~500.
    chico = {'ramo.webp': 320, 'ramo-2.webp': 320, 'banda.webp': 640}.get(destino)
    if chico:
        guardar(img, destino.replace('.webp', '-sm.webp'), chico, quality=calidad, method=6)
