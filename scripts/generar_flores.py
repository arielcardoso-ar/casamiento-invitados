#!/usr/bin/env python3
"""Inyecta la ornamentación botánica generada dentro de invitacion.html."""

import os
import re
import piezas as defs
import ramo as gen_flores

PLANTILLA = os.path.join(os.path.dirname(__file__), '..', 'templates', 'invitacion.html')
W, H = gen_flores.LIENZO

ESQUINAS = ('tl', 'tr', 'bl', 'br')

sprite = f'''    <!-- Ornamentación botánica: el ramo se dibuja una sola vez y las cuatro
         esquinas lo reutilizan con <use>. Generado por scripts/generar_flores.py -->
    <svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
      {defs.todo()}
      <g id="ramoFlores">{gen_flores.ramo()}</g>
    </svg>
'''

corners = '\n'.join(
    f'''    <div class="hero-botanical bot-{c}" aria-hidden="true">
      <svg viewBox="0 0 {W} {H}" focusable="false"><use href="#ramoFlores"/></svg>
    </div>'''
    for c in ESQUINAS
)

bloque = sprite + corners + '\n'

fuente = open(PLANTILLA).read()

# El bloque viejo va desde el comentario del ramo hasta antes de .hero-inner
inicio = fuente.index('    <!-- Ornamentación botánica')
fin = fuente.index('    <div class="hero-inner">')

open(PLANTILLA, 'w').write(fuente[:inicio] + bloque + '\n' + fuente[fin:])

peso = len(bloque) / 1024
print(f'inyectado · {peso:.0f} KB de SVG para las 4 esquinas')
print(re.search(r'id="ramoFlores"', bloque) and 'sprite ok')
