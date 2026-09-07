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
    ("confirmacion-12") para que un reintento no duplique lo que ya entró: si
    la respuesta del envío anterior se perdió en el camino, la fila quedó sin
    marcar en SQLite y se reencola igual.
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
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', ruta)
    with open(local, 'rb') as f:
        return f.read()


# ── Cola en segundo plano ─────────────────────────────────────────────────────

_cola = None
_al_terminar = None    # callback(tipo, id, link) para marcar la fila en SQLite


def iniciar(al_terminar=None):
    """Arranca el hilo que vacía la cola. Se llama una vez, desde app.py."""
    global _cola, _al_terminar
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
        # La foto a Drive sólo si hay OAuth; la fila va igual, con link vacío.
        link = ''
        if CARPETA_DRIVE and hay_oauth():
            link = _subir_a_drive(_bajar(datos['ruta']), datos['nombre'],
                                  datos.get('tipo_mime', 'image/jpeg'))
        _agregar_fila('Fotos', (datos['cuando'], datos['subido_por'],
                                datos['descripcion'], link, datos['ruta']),
                      clave=f"foto-{datos['id']}")
        _marcar('foto', datos['id'], link or 'ok')

    elif tipo == 'cancion':
        _agregar_fila('Canciones', (datos['cuando'], datos['titulo'],
                                    datos['artista'], datos['sugerido_por']),
                      clave=f"cancion-{datos['id']}")
        _marcar('cancion', datos['id'], '')

    elif tipo == 'confirmacion':
        _agregar_fila('Confirmaciones',
                      (datos['cuando'], datos['nombre'], datos['asiste'],
                       datos['restricciones'], datos['mensaje']),
                      clave=f"confirmacion-{datos['id']}")
        _marcar('confirmacion', datos['id'], '')


def _marcar(tipo, fila_id, link):
    if _al_terminar:
        try:
            _al_terminar(tipo, fila_id, link)
        except Exception:
            log.exception('No se pudo marcar %s %s como replicado', tipo, fila_id)
