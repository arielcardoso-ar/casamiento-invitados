#!/usr/bin/env python3
"""
Genera, una sola vez, el permiso para que el sitio escriba en TU Drive.

Por qué OAuth y no una cuenta de servicio: una cuenta de servicio puede escribir
en una planilla que ya existe, pero no puede subir archivos a un Drive personal
—no tiene cuota propia y Google contesta "Service Accounts do not have storage
quota"—. Autorizando con tu cuenta, las fotos quedan a tu nombre, en tu Drive y
contra tu cuota.

Antes de correrlo, en https://console.cloud.google.com:

  1. Creá un proyecto (o usá uno que tengas).
  2. "APIs y servicios" → habilitá **Google Drive API** y **Google Sheets API**.
  3. "Pantalla de consentimiento" → tipo **Externo**, completá lo mínimo y
     agregate a vos mismo como **usuario de prueba**. No hace falta publicarla.
  4. "Credenciales" → Crear credenciales → **ID de cliente de OAuth** → tipo
     **Aplicación de escritorio**. Anotá el ID y el secreto.

Después:

    pip install google-auth-oauthlib
    python scripts/autorizar_google.py

Se abre el navegador, aceptás, y el script imprime las tres variables que hay
que pegar en Render. El token no vence mientras no le revoques el acceso.
"""

import sys

ALCANCES = [
    # `drive.file` es el permiso mínimo: sólo ve y toca los archivos que crea
    # esta app, no el resto de tu Drive.
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print('Falta una librería que sólo se usa acá:\n\n'
              '    pip install google-auth-oauthlib\n')
        return 1

    print(__doc__)
    client_id = input('ID de cliente: ').strip()
    client_secret = input('Secreto de cliente: ').strip()
    if not client_id or not client_secret:
        print('\nSin ID y secreto no hay nada que autorizar.')
        return 1

    flujo = InstalledAppFlow.from_client_config(
        {'installed': {
            'client_id': client_id,
            'client_secret': client_secret,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': ['http://localhost'],
        }},
        scopes=ALCANCES,
    )
    # `consent` + `offline` fuerzan que Google devuelva el refresh token; si ya
    # habías autorizado antes, sin esto no lo manda de nuevo y quedás sin token.
    credenciales = flujo.run_local_server(port=0, prompt='consent',
                                          access_type='offline')

    print('\n' + '─' * 62)
    print('Listo. Cargá esto en Render (Environment):\n')
    print(f'GOOGLE_CLIENT_ID      = {client_id}')
    print(f'GOOGLE_CLIENT_SECRET  = {client_secret}')
    print(f'GOOGLE_REFRESH_TOKEN  = {credenciales.refresh_token}')
    print('\nY además, sacados de la URL de cada uno:\n')
    print('DRIVE_FOLDER_ID       = el id de la carpeta donde van las fotos')
    print('                        drive.google.com/drive/folders/<ESTO>')
    print('SHEET_ID              = el id de la planilla')
    print('                        docs.google.com/spreadsheets/d/<ESTO>/edit')
    print('─' * 62)
    print('\nEl refresh token es una llave a tu Drive: no lo pegues en el repo,')
    print('sólo en las variables de entorno de Render.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
