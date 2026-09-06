#!/usr/bin/env python3
"""
Compone el ramo de esquina.

Las hojas se colocan calculando la tangente de la curva del tallo, así cada una
nace con el ángulo correcto y la rama queda orgánica en vez de repetitiva.
Los tallos arrancan en coordenadas negativas: al recortarse contra el borde del
viewBox parecen continuar fuera de la pantalla.
"""

import math
import random

LIENZO = (320, 360)


# ── Curvas de Bézier cúbicas ──────────────────────────────────────────────────

def bezier(c, t):
    p0, p1, p2, p3 = c
    u = 1 - t
    return (u**3 * p0[0] + 3*u**2*t * p1[0] + 3*u*t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3*u**2*t * p1[1] + 3*u*t**2 * p2[1] + t**3 * p3[1])


def tangente(c, t):
    p0, p1, p2, p3 = c
    u = 1 - t
    dx = 3*u**2*(p1[0]-p0[0]) + 6*u*t*(p2[0]-p1[0]) + 3*t**2*(p3[0]-p2[0])
    dy = 3*u**2*(p1[1]-p0[1]) + 6*u*t*(p2[1]-p1[1]) + 3*t**2*(p3[1]-p2[1])
    return math.degrees(math.atan2(dy, dx))


def d_de(c):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = c
    return f"M{x0:.1f} {y0:.1f} C{x1:.1f} {y1:.1f} {x2:.1f} {y2:.1f} {x3:.1f} {y3:.1f}"


# ── Ramas ─────────────────────────────────────────────────────────────────────

def _hojas(curva, rnd, piezas, desde, hasta, cada, base, merma, apertura):
    salida = []
    t, lado = desde, 1
    while t <= hasta:
        x, y = bezier(curva, t)
        giro = tangente(curva, t) + lado * (apertura + rnd.uniform(-16, 16))
        esc = base * (1 - merma * t) * rnd.uniform(.82, 1.18)
        salida.append(
            f'<use href="#{rnd.choice(piezas)}" transform="translate({x:.1f} {y:.1f}) '
            f'rotate({giro:.1f}) scale({esc:.2f})"/>'
        )
        lado *= -1
        t += cada * rnd.uniform(.75, 1.25)
    return salida


def rama(curva, rnd, grosor=2.6, piezas=('hojaA', 'hojaB'), desde=.05, hasta=.99,
         cada=.072, base=1.0, merma=.5, apertura=52, amp=(.7, 2.1), peso=1.0):
    """
    Tallo + hojas. `peso` es cuánto le pega el viento del cursor: un tallo
    grueso apenas se inmuta, un zarcillo fino se dobla entero.
    """
    cuerpo = [f'<path d="{d_de(curva)}" stroke="url(#tallo)" stroke-width="{grosor}" '
              f'stroke-linecap="round" fill="none"/>']
    cuerpo += _hojas(curva, rnd, piezas, desde, hasta, cada, base, merma, apertura)

    x0, y0 = curva[0]
    return (f'<g class="rama" style="--dur:{rnd.uniform(6.5,12.5):.1f}s;'
            f'--retardo:{-rnd.uniform(0,12):.1f}s;--amp:{rnd.uniform(*amp):.2f}deg;'
            f'--peso:{peso};transform-origin:{x0:.1f}px {y0:.1f}px">'
            + ''.join(cuerpo) + '</g>')


def flor(rnd, tipo, x, y, esc, giro=None, amp=1.6, peso=1.3):
    """Una flor con su propio cabeceo, pivotando en su base."""
    giro = rnd.uniform(0, 360) if giro is None else giro
    return (f'<g class="flor" style="--dur:{rnd.uniform(5.0,9.5):.1f}s;'
            f'--retardo:{-rnd.uniform(0,9):.1f}s;--amp:{amp}deg;--peso:{peso};'
            f'transform-origin:{x:.1f}px {y:.1f}px">'
            f'<use href="#{tipo}" transform="translate({x:.1f} {y:.1f}) '
            f'rotate({giro:.1f}) scale({esc:.2f})"/></g>')


# ── El ramo ───────────────────────────────────────────────────────────────────

def ramo(semilla=7):
    rnd = random.Random(semilla)

    # Capa de atrás: follaje pálido y sin flores. Da profundidad y hace que el
    # ramo no se lea como una calcomanía plana pegada en la esquina.
    fondo = [
        rama(((-50, -20), (60, 30), (130, 60), (250, 96)), rnd, grosor=1.7,
             piezas=('hojaC',), cada=.085, base=.78, apertura=58, amp=(1.2, 2.6), peso=1.5),
        rama(((-30, -50), (30, 40), (60, 120), (96, 250)), rnd, grosor=1.7,
             piezas=('hojaC',), cada=.09, base=.74, apertura=62, amp=(1.2, 2.6), peso=1.4),
        rama(((-44, 30), (40, 90), (90, 130), (170, 190)), rnd, grosor=1.4,
             piezas=('hojaC',), cada=.1, base=.6, apertura=66, amp=(1.4, 3.0), peso=1.7),
    ]

    # Tallos principales. Todos nacen fuera del lienzo.
    maestro  = ((-46, -34), (66, 44), (128, 140), (208, 286))
    alto     = ((-34, -52), (78, -24), (152, 34), (238, 66))
    zarcillo = ((-18, 26), (66, 84), (128, 104), (206, 172))
    corta    = ((-38, 66), (12, 118), (38, 164), (58, 232))
    baja     = ((-24, 96), (56, 132), (86, 196), (104, 288))

    frente = [
        rama(maestro,  rnd, grosor=3.2, cada=.062, base=1.18, apertura=46, peso=0.55),
        rama(alto,     rnd, grosor=2.4, cada=.076, base=.98, apertura=56, peso=0.8),
        rama(zarcillo, rnd, grosor=1.8, cada=.088, base=.72, merma=.4, apertura=64, peso=1.6),
        rama(corta,    rnd, grosor=2.0, cada=.1,   base=.82, apertura=58, peso=1.15),
        rama(baja,     rnd, grosor=1.7, cada=.105, base=.68, apertura=62, peso=1.35),
    ]

    # Flores: una protagonista bien adentro del lienzo y el resto en cascada
    # hacia el centro, alternando tipo y tamaño.
    flores = [
        flor(rnd, 'rosa',    78,  74, 1.00),
        flor(rnd, 'rosaB',  152, 148, 0.72),
        flor(rnd, 'rosaLat', 34, 152, 0.62, giro=-18),
        flor(rnd, 'capullo',132,  46, 0.70, giro=118),
        flor(rnd, 'capullo', 62, 214, 0.58, giro=-42),
        flor(rnd, 'rosita', 196,  96, 0.62),
        flor(rnd, 'rosita', 104, 258, 0.54),
        flor(rnd, 'rosaB',  216, 214, 0.40),
        flor(rnd, 'rosita',  16,  62, 0.44),
    ]

    # Paniculata suelta rellenando los huecos.
    gypso = []
    for _ in range(7):
        curva = rnd.choice((maestro, alto, zarcillo, corta))
        x, y = bezier(curva, rnd.uniform(.15, .9))
        x += rnd.uniform(-30, 30)
        y += rnd.uniform(-30, 30)
        gypso.append(f'<use href="#gypso" transform="translate({x:.1f} {y:.1f}) '
                     f'rotate({rnd.uniform(0,360):.0f}) scale({rnd.uniform(.5,1.05):.2f})"/>')

    return (
        f'<g class="capa-fondo">{"".join(fondo)}</g>'
        f'<g class="capa-frente">{"".join(frente)}</g>'
        f'<g class="gypso">{"".join(gypso)}</g>'
        f'{"".join(flores)}'
    )


if __name__ == '__main__':
    print(ramo())
