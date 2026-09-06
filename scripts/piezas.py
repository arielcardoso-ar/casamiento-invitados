#!/usr/bin/env python3
"""
Piezas botánicas reutilizables.

La clave del realismo acá es la asimetría: cada pétalo lleva su propio jitter
de ángulo, escala y sesgo, así ninguna flor queda perfectamente radial como un
engranaje. El azar es sembrado, de modo que el dibujo es siempre el mismo.
"""

import math
import random

# ── Pétalo de rosa: ancho, ahuecado, con muesca y borde ondulado ──────────────
PETALO = (
    "M0 0 "
    "C-13 -1 -21 -11 -22 -23 "
    "C-22.6 -31 -18 -38.5 -11 -39.8 "
    "C-7 -40.6 -4 -38.6 -2.5 -35 "
    "C-1.6 -32.8 -0.7 -31.6 0 -30 "
    "C0.7 -31.6 1.6 -32.8 2.5 -35 "
    "C4 -38.6 7 -40.6 11 -39.8 "
    "C18 -38.5 22.6 -31 22 -23 "
    "C21 -11 13 -1 0 0 Z"
)


def _corona(rnd, cantidad, escala, relleno, desfase=0.0, jitter=1.0, opacidad=1.0):
    """Un anillo de pétalos con desviaciones propias en cada uno."""
    paso = 360 / cantidad
    salida = []
    for i in range(cantidad):
        giro = desfase + i * paso + rnd.uniform(-9, 9) * jitter
        sx = escala * rnd.uniform(.88, 1.12)
        sy = escala * rnd.uniform(.9, 1.1)
        sesgo = rnd.uniform(-7, 7) * jitter
        salida.append(
            f'<path d="{PETALO}" fill="url(#{relleno})" opacity="{opacidad}" '
            f'transform="rotate({giro:.1f}) scale({sx:.3f} {sy:.3f}) skewX({sesgo:.1f})"/>'
        )
    return ''.join(salida)


def _corazon():
    """Centro enrollado de la rosa: espirales cerradas, no un círculo."""
    return '''<g transform="scale(.4)">
        <ellipse rx="17" ry="15" fill="#a8525f" opacity=".55"/>
        <path d="M-2 -16 C11 -15 17 -3 10 7 C4 15 -8 14 -12 5 C-15 -2 -11 -11 -3 -11"
              fill="none" stroke="#b1606c" stroke-width="6" stroke-linecap="round"/>
        <path d="M0 -9 C7 -8 10 -1 6 4 C3 8 -3 7 -5 3"
              fill="none" stroke="#9d4a58" stroke-width="5.5" stroke-linecap="round"/>
        <path d="M1 -3 C3.5 -2.5 4 0 2.5 1.5"
              fill="none" stroke="#8c3f4d" stroke-width="4" stroke-linecap="round"/>
    </g>'''


def rosa(nombre, semilla, claro=False):
    """
    Rosa de jardín vista desde arriba: cuatro coronas cada vez más cerradas,
    con una sombra propia debajo para despegarla del fondo.
    """
    rnd = random.Random(semilla)
    ext = 'petaloClaro' if claro else 'petaloExt'
    med = 'petaloExt' if claro else 'petaloMed'
    return f'''<g id="{nombre}">
      <ellipse cx="2.5" cy="3.5" rx="35" ry="33" fill="#7d5a5e" opacity=".11"/>
      <g stroke="#c98f96" stroke-width=".45" stroke-opacity=".32" stroke-linejoin="round">
        {_corona(rnd, 6, 1.0, ext)}
        {_corona(rnd, 5, .74, med, desfase=32)}
        {_corona(rnd, 5, .52, 'petaloMed', desfase=63)}
        {_corona(rnd, 4, .34, 'petaloInt', desfase=21)}
      </g>
      {_corazon()}
    </g>'''


def rosa_lateral(nombre, semilla):
    """
    Rosa de tres cuartos: el mismo pétalo pero achatado en vertical y con
    cáliz visible. Tener flores en distinto ángulo es lo que saca al ramo
    de la sensación de calcomanía repetida.
    """
    rnd = random.Random(semilla)
    return f'''<g id="{nombre}">
      <ellipse cx="1.5" cy="6" rx="30" ry="20" fill="#7d5a5e" opacity=".13"/>
      <g transform="scale(1 .68)">
        <g stroke="#c98f96" stroke-width=".5" stroke-opacity=".3" stroke-linejoin="round">
          {_corona(rnd, 5, 1.0, 'petaloExt', desfase=18)}
          {_corona(rnd, 5, .7, 'petaloMed', desfase=48)}
          {_corona(rnd, 4, .44, 'petaloInt', desfase=25)}
        </g>
      </g>
      <g transform="translate(0 12)">
        <path d="M-3 0 C-13 4 -19 -3 -21 -12 C-14 -8 -7 -5 -3 0 Z" fill="url(#hojaVerde)"/>
        <path d="M3 0 C13 4 19 -3 21 -12 C14 -8 7 -5 3 0 Z" fill="url(#hojaVerde)"/>
        <path d="M0 -2 C-1 8 0 16 1 26" stroke="url(#tallo)" stroke-width="2.4"
              stroke-linecap="round" fill="none"/>
      </g>
      {_corazon()}
    </g>'''


def rosita(nombre='rosita'):
    """Flor chica de cinco pétalos, con estambres."""
    rnd = random.Random(11)
    estambres = ''.join(
        f'<line x1="0" y1="0" x2="{5.5*math.cos(math.radians(a)):.1f}" '
        f'y2="{5.5*math.sin(math.radians(a)):.1f}" stroke="#d8b878" stroke-width=".9"/>'
        f'<circle cx="{6.4*math.cos(math.radians(a)):.1f}" '
        f'cy="{6.4*math.sin(math.radians(a)):.1f}" r="1.5" fill="#e8cd94"/>'
        for a in range(0, 360, 45)
    )
    return f'''<g id="{nombre}">
      <ellipse cx="1" cy="1.5" rx="12" ry="11" fill="#7d5a5e" opacity=".09"/>
      <g stroke="#e0aeb2" stroke-width=".4" stroke-opacity=".4">
        {_corona(rnd, 5, .5, 'petaloClaro', jitter=1.2)}
      </g>
      {estambres}
      <circle r="3.4" fill="#dcb96f"/>
      <circle r="1.6" fill="#c39c4f"/>
    </g>'''


def capullo(nombre='capullo'):
    """Capullo de perfil con los pétalos envolviéndose."""
    return f'''<g id="{nombre}">
      <path d="M0 9 C-12.5 4 -15.5 -13 -8.5 -25 C-4 -32.5 4 -32.5 8.5 -25
               C15.5 -13 12.5 4 0 9 Z" fill="url(#petaloMed)"/>
      <path d="M0 8 C-9 4 -12 -12 -6 -23 C-3 -28.5 -1 -28.5 1 -24
               C5 -14 4 2 0 8 Z" fill="url(#petaloExt)" opacity=".95"/>
      <path d="M1 8 C7.5 3 10 -11 6 -22 C4 -27 2.5 -27 1.5 -23
               C-.5 -13 -.5 2 1 8 Z" fill="url(#petaloInt)" opacity=".8"/>
      <path d="M-2 -20 C-5 -12 -5 0 -2 7" fill="none" stroke="#c98f96"
            stroke-width=".6" stroke-opacity=".45"/>
      <g fill="url(#hojaVerde)">
        <path d="M-2.5 8 C-12 12 -18.5 4 -21 -6 C-14 -2.5 -7 1.5 -2.5 8 Z"/>
        <path d="M2.5 8 C12 12 18.5 4 21 -6 C14 -2.5 7 1.5 2.5 8 Z"/>
        <path d="M0 9 C-3 14 -3 18 -6 22 C-4 15 -3 12 -1.5 9 Z"/>
      </g>
      <path d="M0 8 C-1 16 0 22 1 31" stroke="url(#tallo)" stroke-width="2.4"
            stroke-linecap="round" fill="none"/>
    </g>'''


def hoja(nombre, largo, ancho, relleno, borde):
    """Hoja lanceolada con punta, nervadura central, venas y peciolo."""
    l, a = largo, ancho
    contorno = (
        f"M0 0 "
        f"C{l*.14:.1f} {-a*.78:.1f} {l*.5:.1f} {-a*1.18:.1f} {l*.84:.1f} {-a*.62:.1f} "
        f"C{l*.96:.1f} {-a*.34:.1f} {l*1.04:.1f} {-a*.12:.1f} {l*1.13:.1f} 0 "
        f"C{l*1.04:.1f} {a*.12:.1f} {l*.96:.1f} {a*.34:.1f} {l*.84:.1f} {a*.62:.1f} "
        f"C{l*.5:.1f} {a*1.18:.1f} {l*.14:.1f} {a*.78:.1f} 0 0 Z"
    )
    nervio = (f"M{l*.04:.1f} 0 C{l*.4:.1f} {-a*.06:.1f} "
              f"{l*.78:.1f} {-a*.04:.1f} {l*1.1:.1f} 0")

    venas = []
    for f, signo in ((.24, -1), (.44, 1), (.62, -1)):
        venas.append(
            f"M{l*f:.1f} {signo*a*.03:.1f} "
            f"C{l*(f+.1):.1f} {signo*a*.32:.1f} "
            f"{l*(f+.2):.1f} {signo*a*.56:.1f} {l*(f+.26):.1f} {signo*a*.68:.1f}"
        )

    return f'''<g id="{nombre}">
      <path d="M{-l*.14:.1f} {a*.06:.1f} L{l*.06:.1f} 0" stroke="{borde}"
            stroke-width="1.5" stroke-linecap="round" opacity=".8"/>
      <path d="{contorno}" fill="url(#{relleno})" stroke="{borde}"
            stroke-width=".5" stroke-opacity=".4" stroke-linejoin="round"/>
      <path d="{nervio}" stroke="{borde}" stroke-width=".9" stroke-opacity=".5" fill="none"/>
      <g stroke="{borde}" stroke-width=".55" stroke-opacity=".3" fill="none">
        {''.join(f'<path d="{v}"/>' for v in venas)}
      </g>
    </g>'''


def gypso(nombre='gypso'):
    """Ramillete de paniculata, con tallitos y capullos cerrados."""
    rnd = random.Random(5)
    piezas = []
    for _ in range(5):
        ang = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(4, 13)
        x, y = r * math.cos(ang), r * math.sin(ang)
        piezas.append(f'<path d="M0 0 Q{x*.5:.1f} {y*.5:.1f} {x:.1f} {y:.1f}" '
                      f'stroke="#a8bd90" stroke-width=".7" fill="none" opacity=".8"/>')
        e = rnd.uniform(.8, 1.35)
        if rnd.random() < .25:
            piezas.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.9*e:.1f}" '
                          f'fill="#eef2e4" stroke="#cfdcbe" stroke-width=".3"/>')
        else:
            piezas.append(
                f'<g transform="translate({x:.1f} {y:.1f}) scale({e:.2f}) '
                f'rotate({rnd.uniform(0,72):.0f})">'
                + ''.join(f'<ellipse cx="0" cy="-2.9" rx="1.9" ry="2.9" fill="#fffdf8" '
                          f'stroke="#d5dfc6" stroke-width=".35" '
                          f'transform="rotate({i*72})"/>' for i in range(5))
                + '<circle r="1.2" fill="#e6d9a0"/></g>'
            )
    return f'<g id="{nombre}">{"".join(piezas)}</g>'


def gradientes():
    return '''
      <radialGradient id="petaloExt" cx="50%" cy="100%" r="110%">
        <stop offset="0%"   stop-color="#c9757f"/>
        <stop offset="30%"  stop-color="#e29ea6"/>
        <stop offset="66%"  stop-color="#f4c8cb"/>
        <stop offset="88%"  stop-color="#fce6e6"/>
        <stop offset="100%" stop-color="#fffaf9"/>
      </radialGradient>
      <radialGradient id="petaloMed" cx="50%" cy="100%" r="105%">
        <stop offset="0%"   stop-color="#b4626f"/>
        <stop offset="38%"  stop-color="#d98d97"/>
        <stop offset="78%"  stop-color="#efb9be"/>
        <stop offset="100%" stop-color="#fbdedf"/>
      </radialGradient>
      <radialGradient id="petaloInt" cx="50%" cy="100%" r="100%">
        <stop offset="0%"   stop-color="#9d4f5e"/>
        <stop offset="45%"  stop-color="#c47883"/>
        <stop offset="100%" stop-color="#e3a7ae"/>
      </radialGradient>
      <radialGradient id="petaloClaro" cx="50%" cy="100%" r="110%">
        <stop offset="0%"   stop-color="#e59aa2"/>
        <stop offset="40%"  stop-color="#f5c6c9"/>
        <stop offset="80%"  stop-color="#fdeeed"/>
        <stop offset="100%" stop-color="#fffdfc"/>
      </radialGradient>

      <linearGradient id="hojaVerde" x1="0" y1="-.3" x2="1" y2=".4">
        <stop offset="0%"   stop-color="#638050"/>
        <stop offset="34%"  stop-color="#86a06c"/>
        <stop offset="100%" stop-color="#c7d6b0"/>
      </linearGradient>
      <linearGradient id="hojaSalvia" x1="0" y1="-.3" x2="1" y2=".4">
        <stop offset="0%"   stop-color="#7d9668"/>
        <stop offset="38%"  stop-color="#a2b98a"/>
        <stop offset="100%" stop-color="#d6e1c4"/>
      </linearGradient>
      <linearGradient id="hojaClara" x1="0" y1="-.3" x2="1" y2=".4">
        <stop offset="0%"   stop-color="#9ab183"/>
        <stop offset="50%"  stop-color="#c3d3ad"/>
        <stop offset="100%" stop-color="#e3ead6"/>
      </linearGradient>
      <linearGradient id="brilloHoja" x1=".1" y1="-1" x2=".6" y2=".6">
        <stop offset="0%"   stop-color="#ffffff" stop-opacity=".55"/>
        <stop offset="55%"  stop-color="#ffffff" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="tallo" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%"   stop-color="#66804d"/>
        <stop offset="100%" stop-color="#95ad79"/>
      </linearGradient>'''


def todo():
    return '\n    '.join([
        '<defs>',
        gradientes(),
        hoja('hojaA', 34, 13, 'hojaVerde', '#638050'),
        hoja('hojaB', 29, 9.5, 'hojaSalvia', '#7d9668'),
        hoja('hojaC', 21, 8, 'hojaClara', '#9ab183'),
        rosa('rosa', 7),
        rosa('rosaB', 23, claro=True),
        rosa_lateral('rosaLat', 41),
        rosita(),
        capullo(),
        gypso(),
        '</defs>',
    ])


if __name__ == '__main__':
    print(todo())
