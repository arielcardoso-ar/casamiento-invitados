#!/usr/bin/env python3
"""
Configuración central del sitio de invitados.

Todo lo que se muestra en la invitación (nombres, fechas, lugares, contacto,
alias de Mercado Pago) vive acá. Los templates no hardcodean nada.

Cualquier valor puede sobreescribirse por variable de entorno sin tocar código,
lo cual es cómodo para probar en Render sin redeploy de configuración.
"""

import os
from datetime import datetime, timedelta, timezone

# Argentina no aplica horario de verano desde 2009, así que un offset fijo de
# UTC-3 es correcto y evita depender de la base tzdata del contenedor.
ART = timezone(timedelta(hours=-3), name='ART')


def _env(clave, defecto):
    valor = os.environ.get(clave, '').strip()
    return valor or defecto


def _env_dt(clave, defecto_iso):
    """Lee una fecha ISO (naive = hora de Argentina) desde el entorno."""
    crudo = _env(clave, defecto_iso)
    try:
        dt = datetime.fromisoformat(crudo)
    except ValueError:
        dt = datetime.fromisoformat(defecto_iso)
    return dt if dt.tzinfo else dt.replace(tzinfo=ART)


# ── Los novios ────────────────────────────────────────────────────────────────

NOVIA = _env('NOVIA', 'Katherine')
NOVIO = _env('NOVIO', 'Ariel')
NOVIA_CORTO = _env('NOVIA_CORTO', 'Kathy')
NOVIO_CORTO = _env('NOVIO_CORTO', 'Ari')

# ── Fecha del casamiento ──────────────────────────────────────────────────────

# Momento exacto de la ceremonia. Es el objetivo de la cuenta regresiva.
FECHA_EVENTO = _env_dt('FECHA_EVENTO', '2027-01-16T17:30:00')

MESES = ('Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre')

FECHA_DIA_MES = f'{FECHA_EVENTO.day} de {MESES[FECHA_EVENTO.month - 1]}'
FECHA_ANIO = str(FECHA_EVENTO.year)

FECHA_LARGA = _env('FECHA_LARGA', f'{FECHA_DIA_MES} de {FECHA_ANIO}')
FECHA_CORTA = _env('FECHA_CORTA',
                   f'{FECHA_EVENTO.day:02d} · {FECHA_EVENTO.month:02d} · {FECHA_ANIO}')
HORA_CEREMONIA = _env('HORA_CEREMONIA', FECHA_EVENTO.strftime('%H:%M'))

# ── Lugares ───────────────────────────────────────────────────────────────────

CEREMONIA = {
    'titulo': _env('CEREMONIA_TITULO', 'Basílica de Lourdes'),
    'detalle': _env('CEREMONIA_DETALLE', 'Ntra. Sra. de Lourdes · Flores, Buenos Aires'),
    'hora': HORA_CEREMONIA,
    'query': _env(
        'CEREMONIA_MAPA',
        'Basílica Nuestra Señora de Lourdes, Flores, Buenos Aires',
    ),
}

FIESTA = {
    'titulo': _env('FIESTA_TITULO', 'Salón Ble'),
    'detalle': _env('FIESTA_DETALLE', 'A continuación de la ceremonia'),
    'hora': _env('FIESTA_HORA', ''),
    'query': _env('FIESTA_MAPA', 'Salón Ble, Buenos Aires'),
}

# ── Contacto / RSVP ───────────────────────────────────────────────────────────

RSVP_TELEFONO = _env('RSVP_TELEFONO', '+54 11 5963-2661')
RSVP_WHATSAPP = _env('RSVP_WHATSAPP', '541159632661')  # solo dígitos, con país
RSVP_NOMBRE = _env('RSVP_NOMBRE', 'Ari')
RSVP_MENSAJE = _env(
    'RSVP_MENSAJE',
    f'¡Hola! Confirmo mi asistencia al casamiento de {NOVIA_CORTO} y {NOVIO_CORTO} 🌿',
)

# ── Polaroids de la invitación ────────────────────────────────────────────────

# Cuelgan de fondo a lo largo de la invitación, apagadas, y se revelan al entrar
# en pantalla. Van en posición absoluta: **no alargan la página**, se acomodan
# en el aire que ya tienen las secciones.
#
# El orden de la lista es el orden en que aparecen al bajar. `foco` es el
# object-position: la polaroid recorta un cuadrado, así que decide qué parte
# del original sobrevive (subí el segundo número para bajar el encuadre).
# Los archivos los genera scripts/preparar_fotos.py.
POLAROIDS = [
    {'base': 'img/foto-1',  'foco': '50% 32%'},   # helado
    {'base': 'img/foto-2',  'foco': '54% 30%'},   # el lago
    {'base': 'img/foto-3',  'foco': '50% 60%'},   # la cascada
    {'base': 'img/foto-4',  'foco': '55% 38%'},   # abrazados
    {'base': 'img/foto-5',  'foco': '50% 68%'},   # el arco de flores
    {'base': 'img/foto-6',  'foco': '50% 56%'},   # la playa
    {'base': 'img/foto-7',  'foco': '50% 58%'},   # la calle empedrada
    {'base': 'img/foto-8',  'foco': '50% 40%'},   # el beso
    {'base': 'img/foto-9',  'foco': '50% 52%'},   # el mar a contraluz
    {'base': 'img/foto-10', 'foco': '46% 55%'},   # la buganvilla
    {'base': 'img/foto-11', 'foco': '50% 58%'},   # el arco de piedra
    {'base': 'img/foto-12', 'foco': '50% 38%'},   # la mesa
    {'base': 'img/foto-13', 'foco': '52% 42%'},   # las ruinas
    {'base': 'img/foto-14', 'foco': '50% 52%'},   # la cascada verde
    {'base': 'img/foto-15', 'foco': '50% 38%'},   # las mariposas
    {'base': 'img/foto-16', 'foco': '50% 48%'},   # los cascos
    {'base': 'img/foto-17', 'foco': '50% 50%'},   # la tirolesa
    {'base': 'img/foto-18', 'foco': '50% 74%'},   # el vitral
    {'base': 'img/foto-19', 'foco': '52% 52%'},   # el barco
    {'base': 'img/foto-20', 'foco': '50% 48%'},   # la cueva de agua
    {'base': 'img/foto-21', 'foco': '50% 42%'},   # la cabaña
    {'base': 'img/foto-22', 'foco': '50% 50%'},   # la playa de piedras
    {'base': 'img/foto-23', 'foco': '56% 45%'},   # el muelle
    {'base': 'img/foto-24', 'foco': '60% 42%'},   # la playa con sombrero
    {'base': 'img/foto-25', 'foco': '50% 55%'},   # la tortuga
    {'base': 'img/foto-26', 'foco': '50% 45%'},   # la tortuga en el campo
    {'base': 'img/foto-27', 'foco': '50% 55%'},   # la cueva
    {'base': 'img/foto-28', 'foco': '50% 46%'},   # la selva
    {'base': 'img/foto-29', 'foco': '52% 42%'},   # el bambú
    {'base': 'img/foto-30', 'foco': '50% 55%'},   # el atardecer
    {'base': 'img/foto-31', 'foco': '50% 40%'},   # el campo
    {'base': 'img/foto-32', 'foco': '50% 50%'},   # bajo el agua
]

# Dónde puede colgar una foto en cada sección: (lado, ancla, distancia).
# `ancla` dice desde qué borde se mide, y eso es lo que las hace robustas: en
# una sección corta, una arriba y otra abajo nunca se pisan, mida lo que mida.
#
# Cuántas entran por sección no lo decide el gusto sino la aritmética: una
# polaroid mide ~120 px de alto en un celular y ~197 px en escritorio, y las
# secciones cambian de alto entre los dos (en el celular el texto envuelve más,
# así que "detalles" es alto en el celular y bajo en la compu). Estas ranuras
# están calculadas para que dos del mismo lado no se toquen en **ninguno** de
# los dos anchos: dos polaroids superpuestas al 38% se transparentan entre sí y
# quedan como una doble exposición sucia. Las de abajo van un poco más adentro
# porque, al estar giradas, la punta del marco baja más de lo que sugiere el
# rectángulo y la sección se la recortaba.
RANURAS = (
    ('welcome', (('izq', 'arriba', '3%'),  ('der', 'arriba', '10%'),
                 ('izq', 'abajo', '8%'),   ('der', 'abajo', '5%'))),
    ('count',   (('der', 'arriba', '4%'),  ('izq', 'arriba', '12%'),
                 ('der', 'abajo', '7%'),   ('izq', 'abajo', '5%'))),
    ('band',    (('izq', 'arriba', '5%'),  ('der', 'arriba', '12%'),
                 ('izq', 'abajo', '5%'),   ('der', 'abajo', '8%'))),
    ('details', (('izq', 'arriba', '2%'),  ('der', 'arriba', '9%'),
                 ('izq', 'arriba', '38%'), ('der', 'arriba', '45%'),
                 ('izq', 'abajo', '5%'),   ('der', 'abajo', '5%'))),
    ('howto',   (('der', 'arriba', '4%'),  ('izq', 'arriba', '10%'),
                 ('der', 'abajo', '6%'),   ('izq', 'abajo', '5%'))),
    ('rsvp',    (('izq', 'arriba', '4%'),  ('der', 'arriba', '11%'),
                 ('izq', 'abajo', '5%'),   ('der', 'abajo', '7%'))),
    ('actions', (('der', 'arriba', '3%'),  ('izq', 'arriba', '9%'),
                 ('der', 'abajo', '6%'),   ('izq', 'abajo', '5%'))),
    ('closing', (('izq', 'arriba', '6%'),  ('der', 'abajo', '7%'))),
)

# Inclinaciones y tamaños que se van turnando. Las listas son de largo primo
# entre sí, así que la combinación giro+escala tarda en repetirse y no se
# forman parejas de polaroids calcadas.
GIROS = ('-5.5deg', '4deg', '-3deg', '6deg', '-4.5deg', '3.5deg', '-6deg',
         '5deg', '-2.5deg', '4.5deg', '-5deg')
ESCALAS = ('1', '.92', '.86', '.96', '.9', '.88', '.94')


def _polaroids_repartidas():
    """
    Cuelga cada foto en su ranura. Descarta las que no estén en disco, para no
    colgar marcos vacíos, y las ranuras que sobran quedan libres.
    """
    base_static = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    disponibles = [f for f in POLAROIDS
                   if os.path.exists(os.path.join(base_static, f"{f['base']}-480.jpg"))]

    colgadas, i = [], 0
    for zona, ranuras in RANURAS:
        for lado, ancla, distancia in ranuras:
            if i >= len(disponibles):
                return colgadas
            foto = disponibles[i]
            colgadas.append(dict(
                foto,
                zona=zona, lado=lado, ancla=ancla, distancia=distancia,
                giro=GIROS[i % len(GIROS)],
                escala=ESCALAS[i % len(ESCALAS)],
                chica=f"{foto['base']}-240.jpg",
                grande=f"{foto['base']}-480.jpg",
            ))
            i += 1
    return colgadas


# ── Regalo / Mercado Pago ─────────────────────────────────────────────────────

MP_ALIAS = _env('MP_ALIAS', 'arielcardoso.mp')
MP_TITULAR = _env('MP_TITULAR', f'{NOVIO} Cardoso')
MP_CVU = _env('MP_CVU', '')          # opcional: CVU para transferencia bancaria

# Link de cobro propio de Mercado Pago ("Tu Link" o un Link de pago).
# Se genera desde la app: Cobrar → Tu Link. Queda algo como
# https://link.mercadopago.com.ar/tuusuario y el que paga elige el monto.
# Si está cargado, el sitio arma solo el QR que apunta acá.
MP_LINK = _env('MP_LINK', '')

# Alternativa: el QR oficial de Mercado Pago (Cobrar → QR → descargar imagen).
# Es el que leen todas las billeteras. Puede ser una URL completa o el nombre
# de un archivo dentro de static/ (por ejemplo 'img/mp-qr.png').
MP_QR_IMG = _env('MP_QR_IMG', '')

# ── Apertura de la galería y la subida de fotos ───────────────────────────────

# La galería y la subida de fotos permanecen cerradas hasta el evento.
# Por defecto se abren con la ceremonia; se puede adelantar/atrasar por entorno.
APERTURA_FOTOS = _env_dt('APERTURA_FOTOS', FECHA_EVENTO.isoformat())

# Cuánto tiempo después del evento se siguen aceptando fotos (0 = para siempre).
DIAS_SUBIDA_ABIERTA = int(_env('DIAS_SUBIDA_ABIERTA', '0') or 0)


def ahora():
    """Hora actual en Argentina."""
    return datetime.now(ART)


def fotos_abiertas(momento=None):
    """¿Ya se habilitaron la galería y la subida de fotos?"""
    momento = momento or ahora()
    if momento < APERTURA_FOTOS:
        return False
    if DIAS_SUBIDA_ABIERTA > 0:
        return momento <= APERTURA_FOTOS + timedelta(days=DIAS_SUBIDA_ABIERTA)
    return True


def segundos_para_apertura(momento=None):
    """Segundos que faltan para la apertura (0 si ya abrió)."""
    momento = momento or ahora()
    return max(0, int((APERTURA_FOTOS - momento).total_seconds()))


def mapa_embed(query):
    """URL de Google Maps embebible para un lugar."""
    from urllib.parse import quote_plus
    return f'https://maps.google.com/maps?q={quote_plus(query)}&output=embed'


def mapa_link(query):
    """URL de Google Maps para abrir en una pestaña nueva."""
    from urllib.parse import quote_plus
    return f'https://maps.google.com/maps?q={quote_plus(query)}'


def contexto():
    """Diccionario que se inyecta en todos los templates."""
    return {
        'novia': NOVIA,
        'novio': NOVIO,
        'novia_corto': NOVIA_CORTO,
        'novio_corto': NOVIO_CORTO,
        'fecha_larga': FECHA_LARGA,
        'fecha_corta': FECHA_CORTA,
        'fecha_dia_mes': FECHA_DIA_MES,
        'fecha_anio': FECHA_ANIO,
        'fecha_iso': FECHA_EVENTO.isoformat(),
        'hora_ceremonia': HORA_CEREMONIA,
        'ceremonia': dict(CEREMONIA,
                          embed=mapa_embed(CEREMONIA['query']),
                          link=mapa_link(CEREMONIA['query'])),
        'fiesta': dict(FIESTA,
                       embed=mapa_embed(FIESTA['query']),
                       link=mapa_link(FIESTA['query'])),
        'rsvp_telefono': RSVP_TELEFONO,
        'rsvp_nombre': RSVP_NOMBRE,
        'rsvp_url': f'https://wa.me/{RSVP_WHATSAPP}?text={_quote(RSVP_MENSAJE)}',
        'mp_alias': MP_ALIAS,
        'mp_titular': MP_TITULAR,
        'mp_cvu': MP_CVU,
        'mp_link': MP_LINK,
        'polaroids': _polaroids_repartidas(),
        'mp_qr_img': MP_QR_IMG,
        # Hay QR de pago si tenemos un link para codificar o una imagen oficial.
        'mp_qr': bool(MP_LINK or MP_QR_IMG),
        'apertura_iso': APERTURA_FOTOS.isoformat(),
    }


def _quote(texto):
    from urllib.parse import quote
    return quote(texto)
