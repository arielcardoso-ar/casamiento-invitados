#!/usr/bin/env python3
"""
Réplica en Google Drive de todo lo que dejan los invitados.

  Fotos          → un archivo en una carpeta de Drive + una fila en la planilla
  Canciones      → una fila en la planilla
  Confirmaciones → una fila en la planilla

Hay dos caminos para la planilla, y alcanza con uno:

  A. **Webhook de Apps Script** (`SHEET_WEBHOOK_URL`) — el más simple, y el que
     conviene si lo único que querés es la planilla. El script vive dentro de la
     propia hoja, así que no hace falta proyecto en Google Cloud, ni pantalla de
     consentimiento, ni tokens OAuth: se pega el código, se publica y listo.
     Ver `scripts/apps_script_planilla.gs`.

  B. **API de Sheets con OAuth** (`SHEET_ID` + las tres GOOGLE_*) — hace falta
     igual si además querés las fotos en Drive, porque eso el webhook no lo
     cubre. Se autentica como vos y no con una cuenta de servicio: una cuenta de
     servicio escribe bien en una planilla, pero no puede subir archivos a un
     Drive personal —no tiene cuota propia y Google rechaza la subida con
     "Service Accounts do not have storage quota"—. `scripts/autorizar_google.py`
     genera el token una sola vez.

Si están los dos, manda el webhook: es el que menos se rompe.

Y una regla que vale para ambos: **nada de esto puede hacer fallar lo que hizo
el invitado.** Sacó una foto en la fiesta y la está subiendo con el 4G del
salón: si Google está caído o el token venció, la foto igual tiene que entrar.
Todo se encola en un hilo aparte y, si falla, la fila queda sin marcar y se
reintenta después desde `/admin/google`. Nunca se le devuelve un error al
invitado por esto.
"""

import io
import json
import logging
import os
import queue
import threading

log = logging.getLogger(__name__)

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
REFRESH_TOKEN = os.environ.get('GOOGLE_REFRESH_TOKEN', '')
CARPETA_DRIVE = os.environ.get('DRIVE_FOLDER_ID', '')
PLANILLA = os.environ.get('SHEET_ID', '')

# Camino A: el webhook publicado desde la propia planilla.
WEBHOOK_URL = os.environ.get('SHEET_WEBHOOK_URL', '')
WEBHOOK_TOKEN = os.environ.get('SHEET_WEBHOOK_TOKEN', '')

TOKEN_URI = 'https://oauth2.googleapis.com/token'
ALCANCES = ('https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/spreadsheets')

# Cabeceras de cada pestaña. Si la pestaña no existe, se crea con esta fila.
HOJAS = {
    'Fotos': ('Fecha', 'Quién la subió', 'Mensaje', 'Link en Drive', 'Original'),
    'Canciones': ('Fecha', 'Tema', 'Artista', 'Quién la pidió'),
    # Sin columna de acompañantes: la confirmación es individual, uno por fila.
    'Confirmaciones': ('Fecha', 'Nombre', '¿Asiste?', 'Restricciones', 'Mensaje'),
}


def hay_planilla():
    """¿Hay a dónde mandar las filas?"""
    return bool(WEBHOOK_URL or (PLANILLA and hay_oauth()))


def hay_deposito_de_fotos():
    """
    ¿Hay dónde guardar las fotos de forma permanente?

    Importa porque el disco de Render es efímero: sin esto, las fotos de la
    fiesta viven hasta el próximo reinicio del contenedor y después no están
    más. El webhook alcanza; Cloudinary también.
    """
    return bool(WEBHOOK_URL or (CARPETA_DRIVE and hay_oauth()))


def hay_oauth():
    return bool(CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN)


def configurado():
    """¿Hay al menos un destino donde escribir?"""
    return bool(hay_planilla() or (CARPETA_DRIVE and hay_oauth()))


def estado():
    """Qué está configurado y qué falta, para mostrarlo en /admin/google."""
    return {
        'planilla_por_webhook': bool(WEBHOOK_URL),
        'planilla_por_api': bool(PLANILLA and hay_oauth()),
        'credenciales_oauth': hay_oauth(),
        'carpeta_drive': bool(CARPETA_DRIVE and hay_oauth()),
        'activo': configurado(),
        'en_cola': _cola.qsize() if _cola else 0,
        'ultima_restauracion': dict(ultima_restauracion),
    }


# ── Clientes de Google ────────────────────────────────────────────────────────

_servicios = {}
_candado = threading.Lock()


def _servicio(nombre, version):
    """Cliente de la API, creado una sola vez y reutilizado."""
    with _candado:
        if nombre not in _servicios:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            credenciales = Credentials(
                None,
                refresh_token=REFRESH_TOKEN,
                token_uri=TOKEN_URI,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scopes=list(ALCANCES),
            )
            _servicios[nombre] = build(nombre, version, credentials=credenciales,
                                       cache_discovery=False)
        return _servicios[nombre]


# ── Planilla ──────────────────────────────────────────────────────────────────

_hojas_listas = set()


def _asegurar_hoja(nombre):
    """Crea la pestaña con sus cabeceras si todavía no está."""
    if nombre in _hojas_listas:
        return
    hojas = _servicio('sheets', 'v4').spreadsheets()

    existentes = {h['properties']['title']
                  for h in hojas.get(spreadsheetId=PLANILLA).execute()['sheets']}
    if nombre not in existentes:
        hojas.batchUpdate(
            spreadsheetId=PLANILLA,
            body={'requests': [{'addSheet': {'properties': {'title': nombre}}}]},
        ).execute()
        hojas.values().append(
            spreadsheetId=PLANILLA, range=f'{nombre}!A1',
            valueInputOption='USER_ENTERED',
            body={'values': [list(HOJAS[nombre]) + ['id']]},
        ).execute()

    _hojas_listas.add(nombre)


def _agregar_fila(hoja, valores, clave=''):
    """
    Suma una fila a la pestaña. `clave` identifica el registro de forma única
    ("confirmacion-3f9a…", ver database.nueva_clave) para que un reintento no
    duplique lo que ya entró: si la respuesta del envío anterior se perdió en
    el camino, la fila quedó sin marcar en SQLite y se reencola igual.
    """
    fila = [('' if v is None else str(v)) for v in valores]
    if WEBHOOK_URL:
        _agregar_fila_por_webhook(hoja, fila, clave)
    elif PLANILLA:
        _agregar_fila_por_api(hoja, fila, clave)


def _agregar_fila_por_webhook(hoja, fila, clave):
    import urllib.error
    import urllib.request

    cuerpo = json.dumps({
        'token': WEBHOOK_TOKEN,
        'hoja': hoja,
        'cabeceras': list(HOJAS[hoja]) + ['id'],
        'valores': fila + [clave],
        'clave': clave,
    }).encode('utf-8')

    pedido = urllib.request.Request(
        WEBHOOK_URL, data=cuerpo,
        headers={'Content-Type': 'application/json'}, method='POST')

    # Apps Script contesta con un 302 a script.googleusercontent.com; urllib lo
    # sigue solo. Lo que importa es el JSON del final.
    with urllib.request.urlopen(pedido, timeout=45) as r:
        respuesta = json.loads(r.read().decode('utf-8') or '{}')

    if not respuesta.get('ok'):
        raise RuntimeError(f"El webhook rechazó la fila: {respuesta.get('error')}")


def _agregar_fila_por_api(hoja, fila, clave):
    _asegurar_hoja(hoja)
    _servicio('sheets', 'v4').spreadsheets().values().append(
        spreadsheetId=PLANILLA, range=f'{hoja}!A1',
        valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS',
        body={'values': [fila + [clave]]},
    ).execute()


# ── Drive ─────────────────────────────────────────────────────────────────────

def _subir_foto_por_webhook(datos, nombre, tipo_mime='image/jpeg'):
    """
    Manda la foto al Apps Script, que la guarda en Drive y devuelve las URLs
    con las que la galería la va a mostrar.
    """
    import base64
    import urllib.request

    cuerpo = json.dumps({
        'token': WEBHOOK_TOKEN,
        'accion': 'foto',
        'nombre': nombre,
        'tipo': tipo_mime,
        'contenido': base64.b64encode(datos).decode('ascii'),
    }).encode('utf-8')

    pedido = urllib.request.Request(
        WEBHOOK_URL, data=cuerpo,
        headers={'Content-Type': 'application/json'}, method='POST')

    # Generoso: la foto viaja en base64 y Apps Script no es rápido.
    with urllib.request.urlopen(pedido, timeout=180) as r:
        respuesta = json.loads(r.read().decode('utf-8') or '{}')

    if not respuesta.get('ok'):
        raise RuntimeError(f"El webhook rechazó la foto: {respuesta.get('error')}")
    return respuesta


def _achicar(datos, lado_max=2560, calidad=88):
    """
    Reduce la foto antes de mandarla.

    Dos razones: una foto de celular de 8 MB en base64 son ~11 MB de request y
    Apps Script se atraganta; y 100 invitados subiendo originales llenarían el
    Drive. A 2560 px sigue siendo más grande que cualquier pantalla.
    """
    from PIL import Image, ImageOps

    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(datos)))
        if max(img.size) <= lado_max and len(datos) < 2_000_000:
            return datos, 'image/jpeg' if img.format == 'JPEG' else None
        img = img.convert('RGB')
        img.thumbnail((lado_max, lado_max), Image.LANCZOS)
        salida = io.BytesIO()
        img.save(salida, 'JPEG', quality=calidad, optimize=True, progressive=True)
        return salida.getvalue(), 'image/jpeg'
    except Exception:
        # Si Pillow no puede con el formato, va tal cual: mejor grande que nada.
        log.warning('No se pudo achicar la foto; se manda como vino')
        return datos, None


def _subir_a_drive(datos, nombre, tipo_mime='image/jpeg'):
    """Sube los bytes a la carpeta y devuelve el link para ver el archivo."""
    if not CARPETA_DRIVE:
        return ''
    from googleapiclient.http import MediaIoBaseUpload

    archivo = _servicio('drive', 'v3').files().create(
        body={'name': nombre, 'parents': [CARPETA_DRIVE]},
        media_body=MediaIoBaseUpload(io.BytesIO(datos), mimetype=tipo_mime,
                                     resumable=False),
        fields='id,webViewLink',
        supportsAllDrives=True,
    ).execute()
    return archivo.get('webViewLink', '')


def _bajar(ruta):
    """
    Trae los bytes de la foto. En producción `ruta` es la URL de Cloudinary;
    en local, un archivo en static/. Bajarla en vez de arrastrar los bytes
    desde el request mantiene la cola liviana y permite reintentar viejas.
    """
    if ruta.startswith(('http://', 'https://')):
        import urllib.request
        with urllib.request.urlopen(ruta, timeout=60) as r:
            return r.read()
    if ruta.startswith('uploads/') and CARPETA_SUBIDAS:
        # En Render las subidas van a /tmp/uploads, no a static/: buscarlas en
        # static/ hacía que ninguna foto de la fiesta llegara nunca a Drive.
        local = os.path.join(CARPETA_SUBIDAS, ruta[len('uploads/'):])
    else:
        local = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', ruta)
    with open(local, 'rb') as f:
        return f.read()


# ── Cola en segundo plano ─────────────────────────────────────────────────────

_cola = None
_al_terminar = None
CARPETA_SUBIDAS = ''   # dónde guarda app.py las fotos sin Cloudinary    # callback(tipo, id, link) para marcar la fila en SQLite


def iniciar(al_terminar=None, carpeta_subidas=''):
    """Arranca el hilo que vacía la cola. Se llama una vez, desde app.py."""
    global _cola, _al_terminar, CARPETA_SUBIDAS
    CARPETA_SUBIDAS = carpeta_subidas
    if _cola is not None or not configurado():
        return
    _al_terminar = al_terminar
    _cola = queue.Queue(maxsize=500)
    threading.Thread(target=_trabajar, name='google-sync', daemon=True).start()
    log.info('Réplica en Google activada')


def encolar(tipo, **datos):
    """Agenda un envío. Si no hay nada configurado, no hace nada."""
    if _cola is None:
        return False
    try:
        _cola.put_nowait((tipo, datos))
        return True
    except queue.Full:
        log.warning('Cola de Google llena; %s queda para el reintento manual', tipo)
        return False


def _trabajar():
    while True:
        tipo, datos = _cola.get()
        try:
            _despachar(tipo, datos)
        except Exception:
            # Queda sin marcar en la base: /admin/google lo reintenta.
            log.exception('No se pudo replicar %s en Google', tipo)
        finally:
            _cola.task_done()


def _despachar(tipo, datos):
    if tipo == 'foto':
        link, rutas = '', None

        if WEBHOOK_URL:
            crudo = _bajar(datos['ruta'])
            achicada, tipo_mime = _achicar(crudo)
            respuesta = _subir_foto_por_webhook(
                achicada, datos['nombre'],
                tipo_mime or datos.get('tipo_mime', 'image/jpeg'))
            link = respuesta.get('enDrive', '')
            # Si la foto vivía en el disco efímero de Render, la galería tiene
            # que dejar de apuntar ahí: ese archivo desaparece en el próximo
            # reinicio. Desde ahora se sirve desde Drive.
            if not datos['ruta'].startswith('http'):
                rutas = (respuesta.get('ver', ''), respuesta.get('miniatura', ''))

        elif CARPETA_DRIVE and hay_oauth():
            link = _subir_a_drive(_bajar(datos['ruta']), datos['nombre'],
                                  datos.get('tipo_mime', 'image/jpeg'))

        _agregar_fila('Fotos', (datos['cuando'], datos['subido_por'],
                                datos['descripcion'], link, datos['ruta']),
                      clave=datos['clave'])
        _marcar('foto', datos['id'], link or 'ok', rutas)

    elif tipo == 'cancion':
        _agregar_fila('Canciones', (datos['cuando'], datos['titulo'],
                                    datos['artista'], datos['sugerido_por']),
                      clave=datos['clave'])
        _marcar('cancion', datos['id'], '')

    elif tipo == 'confirmacion':
        _agregar_fila('Confirmaciones',
                      (datos['cuando'], datos['nombre'], datos['asiste'],
                       datos['restricciones'], datos['mensaje']),
                      clave=datos['clave'])
        _marcar('confirmacion', datos['id'], '')


# ── Restauración: leer la planilla de vuelta ─────────────────────────────────

def _leer_hoja(hoja):
    """
    Todas las filas de una pestaña, como diccionarios {cabecera: valor}.
    La última columna, la oculta, viene como 'id': es la clave del registro.
    """
    if WEBHOOK_URL:
        return _leer_hoja_por_webhook(hoja)
    if PLANILLA and hay_oauth():
        return _leer_hoja_por_api(hoja)
    return []


def _leer_hoja_por_webhook(hoja):
    import urllib.request

    # Por POST y no por GET: el token no tiene que quedar en ninguna URL.
    cuerpo = json.dumps({'token': WEBHOOK_TOKEN, 'accion': 'leer',
                         'hoja': hoja}).encode('utf-8')
    pedido = urllib.request.Request(
        WEBHOOK_URL, data=cuerpo,
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(pedido, timeout=60) as r:
        respuesta = json.loads(r.read().decode('utf-8') or '{}')

    if not respuesta.get('ok'):
        # Un script viejo, publicado antes de que existiera 'leer', contesta
        # como si fuera una fila más: lo decimos claro para /admin/google.
        raise RuntimeError(respuesta.get('error') or
                           'el script de la planilla no sabe leer: publicá la versión nueva')
    if 'filas' not in respuesta:
        raise RuntimeError('el script de la planilla no sabe leer: publicá la versión nueva')
    return respuesta['filas']


def _leer_hoja_por_api(hoja):
    hojas = _servicio('sheets', 'v4').spreadsheets()
    existentes = {h['properties']['title']
                  for h in hojas.get(spreadsheetId=PLANILLA).execute()['sheets']}
    if hoja not in existentes:
        return []
    valores = hojas.values().get(
        spreadsheetId=PLANILLA, range=hoja,
        valueRenderOption='FORMATTED_VALUE').execute().get('values', [])
    if len(valores) < 2:
        return []
    cabeceras = valores[0]
    return [dict(zip(cabeceras, fila + [''] * (len(cabeceras) - len(fila))))
            for fila in valores[1:]]


def _a_utc(texto):
    """
    '16/01/2027 23:40' (hora de Argentina, como la escribe el sitio) →
    '2027-01-17 02:40:00' (UTC, como la guarda SQLite). Si no se entiende,
    None: la fila entra igual, con la fecha de ahora.
    """
    from datetime import datetime, timezone, timedelta

    texto = str(texto or '').strip()
    for formato in ('%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y',
                    '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d %H:%M:%S'):
        try:
            momento = datetime.strptime(texto, formato)
        except ValueError:
            continue
        if formato.endswith('Z'):
            momento = momento.replace(tzinfo=timezone.utc)
        else:
            momento = momento.replace(tzinfo=timezone(timedelta(hours=-3)))
        return momento.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    return None


def _id_de_drive(link):
    """El ID del archivo a partir de su link (…/file/d/<ID>/view)."""
    import re
    encontrado = re.search(r'/d/([A-Za-z0-9_-]{10,})', link or '') or \
        re.search(r'[?&]id=([A-Za-z0-9_-]{10,})', link or '')
    return encontrado.group(1) if encontrado else ''


def _registro(tipo, fila):
    """Pasa una fila de la planilla al formato de database.restaurar()."""
    clave = str(fila.get('id') or '').strip()
    if not clave.startswith(tipo + '-'):
        return None   # fila escrita a mano o sin clave: no es nuestra
    fecha = _a_utc(fila.get('Fecha'))

    if tipo == 'cancion':
        if not str(fila.get('Tema') or '').strip():
            return None
        return {'clave': clave, 'fecha': fecha, 'titulo': fila['Tema'],
                'artista': fila.get('Artista', ''),
                'sugerido_por': fila.get('Quién la pidió', '')}

    if tipo == 'confirmacion':
        if not str(fila.get('Nombre') or '').strip():
            return None
        asiste = str(fila.get('¿Asiste?', 'Sí')).strip().lower() not in ('no', 'false', '0')
        return {'clave': clave, 'fecha': fecha, 'nombre': fila['Nombre'],
                'asiste': asiste, 'restricciones': fila.get('Restricciones', ''),
                'mensaje': fila.get('Mensaje', '')}

    if tipo == 'foto':
        original = str(fila.get('Original') or '')
        en_drive = str(fila.get('Link en Drive') or '')
        if original.startswith('http'):
            # Cloudinary: la galería la seguía sirviendo desde ahí.
            ruta, miniatura = original, ''
        elif _id_de_drive(en_drive):
            # Estaba en el disco de Render y ahora vive en Drive.
            archivo = _id_de_drive(en_drive)
            ruta = f'https://lh3.googleusercontent.com/d/{archivo}'
            miniatura = ruta + '=w600'
        else:
            return None   # no quedó copia en ningún lado que podamos mostrar
        return {'clave': clave, 'fecha': fecha, 'ruta': ruta,
                'thumbnail': miniatura, 'drive_link': en_drive,
                'subido_por': fila.get('Quién la subió', ''),
                'descripcion': fila.get('Mensaje', '')}
    return None


ultima_restauracion = {}


def restaurar(guardar):
    """
    Trae de vuelta desde la planilla todo lo que el SQLite no tiene.

    `guardar(tipo, registros)` lo inserta y devuelve cuántos eran nuevos
    (database.restaurar). Se llama al arrancar, en un hilo aparte, y a mano
    desde /admin/google?restaurar=1. Devuelve {tipo: cantidad o error}.
    """
    from datetime import datetime

    resultado = {}
    if not hay_planilla():
        return resultado
    for tipo, hoja in (('confirmacion', 'Confirmaciones'),
                       ('cancion', 'Canciones'), ('foto', 'Fotos')):
        try:
            registros = [r for r in (_registro(tipo, f) for f in _leer_hoja(hoja)) if r]
            resultado[tipo] = guardar(tipo, registros)
        except Exception as e:
            # Sin nombres ni contenidos en el log: sólo qué pestaña falló.
            log.warning('No se pudo restaurar %s desde la planilla: %s', hoja, e)
            resultado[tipo] = f'error: {e}'
    ultima_restauracion.clear()
    ultima_restauracion.update(resultado, cuando=datetime.utcnow().isoformat(timespec='seconds'))
    log.info('Restauración desde la planilla: %s', resultado)
    return resultado


def restaurar_en_segundo_plano(guardar):
    """Arranca restaurar() sin demorar el arranque del sitio."""
    if hay_planilla():
        threading.Thread(target=restaurar, args=(guardar,),
                         name='restaurar-planilla', daemon=True).start()


def _marcar(tipo, fila_id, link, rutas=None):
    if _al_terminar:
        try:
            _al_terminar(tipo, fila_id, link, rutas)
        except Exception:
            log.exception('No se pudo marcar %s %s como replicado', tipo, fila_id)
