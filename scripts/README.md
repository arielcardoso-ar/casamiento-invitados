# Generador de la ornamentación botánica

El ramo de flores de la invitación no está dibujado a mano: se genera acá y se
inyecta dentro de `templates/invitacion.html`.

```bash
cd scripts && ../.venv/bin/python generar_flores.py
```

- **`piezas.py`** — las piezas sueltas (rosas, capullos, hojas, paniculata) con
  sus degradés. Cada pétalo lleva jitter propio de ángulo, escala y sesgo: sin
  esa asimetría las flores quedan con cara de engranaje.
- **`ramo.py`** — la composición. Las hojas se ubican calculando la tangente de
  la curva del tallo, así cada una nace con el ángulo correcto. Los tallos
  arrancan en coordenadas negativas para que, al recortarse contra el borde de
  la pantalla, la guirnalda parezca seguir afuera.
- **`generar_flores.py`** — arma el sprite y reemplaza el bloque del template.

El SVG se define **una sola vez** y las cuatro esquinas lo reutilizan con
`<use>`: 42 KB en lugar de 170. El viento del cursor viaja por la variable CSS
`--viento`, que se hereda hasta dentro del árbol clonado, y ahí cada rama la
multiplica por su `--peso`.

Si tocás algo acá, volvé a correr el script y revisá la invitación: el bloque
del template se reescribe entero.

---

# Preparación de las fotos del hero

**`preparar_fotos.py`** — deja las fotos de los novios listas para la web.

```bash
cd scripts && ../.venv/bin/python preparar_fotos.py ~/Downloads/una.jpg ~/Downloads/otra.jpg
```

Genera `static/img/hero-N-900.jpg` y `hero-N-1800.jpg`. Los dos anchos son para
el `srcset` de la invitación: un celular baja ~120 KB en vez de 1 MB. Aplica la
orientación EXIF, que si no las fotos verticales salen acostadas en el navegador.

Después hay que declararlas en `FOTOS_HERO`, en `config.py`, con su `foco`.
