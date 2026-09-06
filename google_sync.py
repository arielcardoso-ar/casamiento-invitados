#!/usr/bin/env python3
"""
Réplica en Google Drive de todo lo que dejan los invitados.

  Fotos          → un archivo en una carpeta de Drive + una fila en la planilla
  Canciones      → una fila en la planilla
  Confirmaciones → una fila en la planilla

Dos decisiones que vale la pena entender antes de tocar esto:

1. **Se autentica como vos, no con una cuenta de servicio.** Una cuenta de
   servicio sirve para escribir en una planilla que ya existe, pero no puede
   subir archivos a un Drive personal: no tiene cuota propia y Google rechaza
   la subida con "Service Accounts do not have storage quota". Con OAuth los
   archivos quedan a tu nombre, en tu Drive y contra tu cuota, que es lo que
   se quiere. `scripts/autorizar_google.py` genera el token una sola vez.

2. **Nada de esto puede hacer fallar una subida.** El invitado sacó una foto en
   la fiesta y la está subiendo con el 4G del salón: si Drive está caído o el
   token venció, la foto igual tiene que entrar. Todo se encola en un hilo
   aparte y, si falla, la fila queda sin marcar y se reintenta después con
   `/admin/google`. Nunca se le devuelve un error al invitado por esto.
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

TOKEN_URI = 'https://oauth2.googleapis.com/token'
ALCANCES = ('https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/spreadsheets')

# Cabeceras de cada pestaña. Si la pestaña no existe, se crea con esta fila.
HOJAS = {
    'Fotos': ('Fecha', 'Quién la subió', 'Mensaje', 'Link en Drive', 'Original'),
    'Canciones': ('Fecha', 'Tema', 'Artista', 'Quién la pidió'),
    'Confirmaciones': ('Fecha', 'Nombre', '¿Asiste?', 'Cuántos', 'Restricciones', 'Mensaje'),
}


def configurado():
    """¿Hay credenciales y al menos un destino donde escribir?"""
    return bool(CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN
                and (CARPETA_DRIVE or PLANILLA))


def estado():
    """Qué está configurado y qué falta, para mostrarlo en /admin/google."""
    return {
        'credenciales': bool(CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN),
        'carpeta_drive': bool(CARPETA_DRIVE),
        'planilla': bool(PLANILLA),
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
            body={'values': [list(HOJAS[nombre])]},
        ).execute()

    _hojas_listas.add(nombre)


def _agregar_fila(hoja, valores):
    if not PLANILLA:
        return
    _asegurar_hoja(hoja)
    _servicio('sheets', 'v4').spreadsheets().values().append(
        spreadsheetId=PLANILLA, range=f'{hoja}!A1',
        valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS',
        body={'values': [[('' if v is None else str(v)) for v in valores]]},
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
        link = _subir_a_drive(_bajar(datos['ruta']), datos['nombre'],
                              datos.get('tipo_mime', 'image/jpeg'))
        _agregar_fila('Fotos', (datos['cuando'], datos['subido_por'],
                                datos['descripcion'], link, datos['ruta']))
        _marcar('foto', datos['id'], link)

    elif tipo == 'cancion':
        _agregar_fila('Canciones', (datos['cuando'], datos['titulo'],
                                    datos['artista'], datos['sugerido_por']))
        _marcar('cancion', datos['id'], '')

    elif tipo == 'confirmacion':
        _agregar_fila('Confirmaciones',
                      (datos['cuando'], datos['nombre'], datos['asiste'],
                       datos['acompanantes'], datos['restricciones'],
                       datos['mensaje']))
        _marcar('confirmacion', datos['id'], '')


def _marcar(tipo, fila_id, link):
    if _al_terminar:
        try:
            _al_terminar(tipo, fila_id, link)
        except Exception:
            log.exception('No se pudo marcar %s %s como replicado', tipo, fila_id)
