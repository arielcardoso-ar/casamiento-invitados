#!/usr/bin/env python3
"""
Sitio público del casamiento de Katherine & Ariel.

Tres cosas para los invitados:
  1. La invitación               →  /
  2. La galería compartida       →  /galeria   (se habilita recién el día del evento)
  3. Subir fotos durante la fiesta →  /fotos    (idem)
  + el regalo por Mercado Pago   →  /regalo

Las fotos se persisten en Cloudinary; SQLite funciona como índice local.
"""

import io
import os
import uuid
from datetime import datetime, timezone
from functools import wraps

import cloudinary
import cloudinary.api
import cloudinary.uploader
from flask import (Flask, jsonify, redirect, render_template, request,
                   send_file, send_from_directory, session, url_for)
from werkzeug.utils import secure_filename

import config
from database import CasamientoDatabase

# HEIC/HEIF de iPhone: sin esto Pillow no puede abrirlos en el modo local.
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:  # pragma: no cover - el entorno puede no tener pillow-heif
    pass


app = Flask(__name__)

# La clave sólo firma la cookie de "desbloqueo" para que los novios puedan
# previsualizar la galería antes del evento. No hay datos sensibles en sesión.
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(32)

MAX_FOTO_BYTES = 25 * 1024 * 1024          # 25 MB por foto
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024   # margen sobre el archivo
app.config['UPLOAD_FOLDER'] = '/tmp/uploads' if os.environ.get('RENDER') else 'static/uploads'

# En local recargamos los templates al vuelo: así se puede retocar el texto de
# la invitación sin reiniciar el servidor. En Render se sirven cacheados.
app.config['TEMPLATES_AUTO_RELOAD'] = not os.environ.get('RENDER')

EXTENSIONES = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif', 'webp'}

# En producción (Render) hay que definir ADMIN_SECRET a mano: sin él quedan
# deshabilitados tanto el sync como la vista previa de la galería. En local
# alcanza con ?unlock=preview para ver cómo queda todo el día del evento.
ADMIN_SECRET = os.environ.get('ADMIN_SECRET') or ('' if os.environ.get('RENDER') else 'preview')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── Cloudinary ────────────────────────────────────────────────────────────────

CLOUDINARY_ENABLED = bool(os.environ.get('CLOUDINARY_CLOUD_NAME'))
CLOUDINARY_FOLDER = os.environ.get('CLOUDINARY_FOLDER', 'casamiento-katherine-ariel')

if CLOUDINARY_ENABLED:
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True,
    )

db = CasamientoDatabase()


# ── Apertura de la galería ────────────────────────────────────────────────────

def desbloqueado():
    """True si el visitante tiene el pase de vista previa de los novios."""
    return bool(session.get('preview'))


def fotos_habilitadas():
    """La galería y la subida están abiertas para este visitante."""
    return config.fotos_abiertas() or desbloqueado()


def requiere_apertura(f):
    """Bloquea un endpoint de API hasta que se habiliten las fotos."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not fotos_habilitadas():
            return jsonify({
                'success': False,
                'abierto': False,
                'message': 'La galería se habilita el día del casamiento.',
                'segundos_restantes': config.segundos_para_apertura(),
            }), 403
        return f(*args, **kwargs)
    return wrapper


@app.before_request
def aplicar_pase_de_vista_previa():
    """`?unlock=<ADMIN_SECRET>` deja ver la galería antes de tiempo."""
    # Sólo en GET: redirigir un POST se llevaría puesto el cuerpo de la subida.
    if request.method != 'GET':
        return None
    token = request.args.get('unlock')
    if token is None:
        return None
    if ADMIN_SECRET and token == ADMIN_SECRET:
        session['preview'] = True
    elif token == '':
        session.pop('preview', None)
    # Redirige a la misma URL sin el token, para no dejarlo en la barra.
    limpio = {k: v for k, v in request.args.items(multi=True) if k != 'unlock'}
    return redirect(url_for(request.endpoint, **limpio) if request.endpoint else '/')


def _fuente_qr_mp():
    """
    De dónde sale la imagen del QR de pago. Preferimos el QR oficial que baja
    Mercado Pago desde la app (lo leen todas las billeteras); si no hay,
    generamos uno que apunta al link de cobro.
    """
    if config.MP_QR_IMG:
        if config.MP_QR_IMG.startswith(('http://', 'https://')):
            return config.MP_QR_IMG
        return url_for('static', filename=config.MP_QR_IMG)
    if config.MP_LINK:
        return url_for('qr_code', to='pago')
    return ''


@app.context_processor
def inyectar_contexto():
    ctx = config.contexto()
    ctx['fotos_abiertas'] = fotos_habilitadas()
    ctx['segundos_para_apertura'] = config.segundos_para_apertura()
    ctx['vista_previa'] = desbloqueado()
    ctx['mp_qr_src'] = _fuente_qr_mp()
    # El QR oficial ya trae el monto abierto y lo escanean todas las billeteras.
    ctx['mp_qr_oficial'] = bool(config.MP_QR_IMG)
    return ctx


# ── Páginas ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('invitacion.html')


@app.route('/fotos')
def fotos():
    if not fotos_habilitadas():
        return render_template('bloqueado.html',
                               pestania='Subir fotos',
                               titulo='Las fotos se suben el día del casamiento',
                               copy='Vas a poder subir las tuyas apenas empiece la '
                                    'celebración. Guardá el link y volvé ese día.'), 200
    return render_template('fotos.html')


@app.route('/galeria')
def galeria():
    if not fotos_habilitadas():
        return render_template('bloqueado.html',
                               pestania='Galería',
                               titulo='La galería se abre el día del casamiento',
                               copy='El álbum compartido se llena esa noche, con las '
                                    'fotos que suban todos los invitados.'), 200
    return render_template('galeria.html', fotos=listar_fotos())


@app.route('/regalo')
def regalo():
    return render_template('regalo.html')


@app.route('/qr-page')
def qr_page():
    return render_template('qr.html')


@app.route('/healthz')
def healthz():
    return jsonify({'ok': True, 'abierto': config.fotos_abiertas()})


# ── QR ────────────────────────────────────────────────────────────────────────

@app.route('/qr')
def qr_code():
    """
    QR del sitio. `?to=fotos|galeria|regalo` apunta a una sección puntual.
    `?to=pago` codifica el link de cobro de Mercado Pago, para que el invitado
    caiga directo en la pantalla de pago en vez de pasar por el sitio.
    """
    import qrcode

    pedido = request.args.get('to', '')

    if pedido == 'pago':
        if not config.MP_LINK:
            return jsonify({'error': 'MP_LINK no configurado'}), 404
        url = config.MP_LINK
    else:
        destinos = {'': '', 'fotos': 'fotos', 'galeria': 'galeria', 'regalo': 'regalo'}
        destino = destinos.get(pedido, '')
        url = request.host_url.rstrip('/') + ('/' + destino if destino else '/')

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=10, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#3b4c33', back_color='white')

    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/estado')
def api_estado():
    """Estado de apertura; la pantalla bloqueada lo consulta para abrirse sola."""
    return jsonify({
        'abierto': fotos_habilitadas(),
        'segundos_restantes': config.segundos_para_apertura(),
        'apertura': config.APERTURA_FOTOS.isoformat(),
        'vista_previa': desbloqueado(),
    })


def listar_fotos():
    """Fotos listas para mostrar: miniatura garantizada y hora local legible."""
    fotos = db.get_fotos()
    if not fotos:
        fotos = _recuperar_indice_si_hace_falta()
    for foto in fotos:
        foto['thumbnail'] = foto.get('thumbnail') or foto['ruta']
        foto['subido_por'] = foto.get('subido_por') or 'Invitado'
        foto['cuando'] = _hora_local(foto.get('fecha_subida'))
    return fotos


def _hora_local(marca):
    """SQLite guarda CURRENT_TIMESTAMP en UTC; lo pasamos a hora de Argentina."""
    if not marca:
        return ''
    try:
        utc = datetime.strptime(str(marca)[:19], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''
    local = utc.replace(tzinfo=timezone.utc).astimezone(config.ART)
    if local.date() == config.ahora().date():
        return local.strftime('%H:%M')
    return local.strftime('%d/%m · %H:%M')


@app.route('/api/fotos')
@requiere_apertura
def api_get_fotos():
    return jsonify(listar_fotos())


def _thumbnail_url(url: str) -> str:
    """URL de miniatura 500×500 derivada de la URL original de Cloudinary."""
    return url.replace('/upload/', '/upload/w_500,h_500,c_fill,g_auto,q_auto,f_auto/', 1)


def _extension_ok(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSIONES


def _subir_a_cloudinary(datos: bytes, nombre_original: str,
                        subido_por: str, descripcion: str) -> dict:
    public_id = (f"{CLOUDINARY_FOLDER}/"
                 f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}")

    resultado = cloudinary.uploader.upload(
        io.BytesIO(datos),
        public_id=public_id,
        resource_type='image',
        overwrite=False,
        quality='auto',
        fetch_format='auto',
        context={
            'subido_por': subido_por,
            'descripcion': descripcion,
            'nombre_original': nombre_original,
        },
    )

    url = resultado['secure_url']
    return {'ruta': url, 'thumbnail': _thumbnail_url(url),
            'nombre_archivo': resultado['public_id']}


def _guardar_local(datos: bytes, nombre_original: str) -> dict:
    """Fallback de desarrollo: redimensiona y guarda en disco."""
    from PIL import Image

    base = secure_filename(nombre_original) or 'foto.jpg'
    nombre = (f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
              f"{uuid.uuid4().hex[:8]}_{base.rsplit('.', 1)[0]}.jpg")

    carpeta = app.config['UPLOAD_FOLDER']
    thumbs = os.path.join(carpeta, 'thumbnails')
    os.makedirs(thumbs, exist_ok=True)

    img = Image.open(io.BytesIO(datos))
    img = img.convert('RGB')

    grande = img.copy()
    grande.thumbnail((1600, 1600), Image.LANCZOS)
    grande.save(os.path.join(carpeta, nombre), 'JPEG', optimize=True, quality=86)

    chica = img.copy()
    chica.thumbnail((500, 500), Image.LANCZOS)
    chica.save(os.path.join(thumbs, nombre), 'JPEG', optimize=True, quality=80)

    return {'ruta': f'uploads/{nombre}',
            'thumbnail': f'uploads/thumbnails/{nombre}',
            'nombre_archivo': nombre}


def _procesar(archivo, subido_por: str, descripcion: str) -> int:
    datos = archivo.read()
    if not datos:
        raise ValueError('archivo vacío')
    if len(datos) > MAX_FOTO_BYTES:
        raise ValueError('la foto supera los 25 MB')

    if CLOUDINARY_ENABLED:
        urls = _subir_a_cloudinary(datos, archivo.filename, subido_por, descripcion)
    else:
        urls = _guardar_local(datos, archivo.filename)

    return db.agregar_foto({
        'nombre_archivo': urls['nombre_archivo'],
        'nombre_original': archivo.filename,
        'ruta': urls['ruta'],
        'thumbnail': urls['thumbnail'],
        'subido_por': subido_por,
        'descripcion': descripcion,
    })


@app.route('/api/fotos/upload', methods=['POST'])
@requiere_apertura
def api_upload_foto():
    archivos = [f for f in request.files.getlist('fotos') if f and f.filename]
    if not archivos:
        return jsonify({'success': False, 'message': 'No se enviaron fotos'}), 400

    subido_por = (request.form.get('nombre') or '').strip()[:60] or 'Invitado'
    descripcion = (request.form.get('descripcion') or '').strip()[:280]

    subidas, errores = 0, []
    for archivo in archivos:
        if not _extension_ok(archivo.filename):
            errores.append(f'{archivo.filename}: formato no permitido')
            continue
        try:
            _procesar(archivo, subido_por, descripcion)
            subidas += 1
        except Exception as e:
            app.logger.exception('Error subiendo %s', archivo.filename)
            errores.append(f'{archivo.filename}: {e}')

    if not subidas:
        return jsonify({'success': False,
                        'message': errores[0] if errores else 'No se pudo subir la foto',
                        'errores': errores}), 400

    plural = 's' if subidas > 1 else ''
    return jsonify({'success': True, 'subidas': subidas, 'errores': errores,
                    'message': f'{subidas} foto{plural} subida{plural}'})


@app.errorhandler(413)
def demasiado_grande(_e):
    return jsonify({'success': False,
                    'message': 'La foto es demasiado grande (máximo 25 MB)'}), 413


# ── Recuperación del índice ───────────────────────────────────────────────────

def _sincronizar_desde_cloudinary():
    """Vuelca en SQLite todo lo que haya en la carpeta de Cloudinary."""
    conn = db.get_connection()
    conn.execute('DELETE FROM fotos')
    conn.commit()
    conn.close()

    importadas, cursor = 0, None
    while True:
        params = dict(type='upload', prefix=CLOUDINARY_FOLDER,
                      max_results=100, context=True)
        if cursor:
            params['next_cursor'] = cursor

        resultado = cloudinary.api.resources(**params)
        for recurso in resultado.get('resources', []):
            ctx = recurso.get('context', {}).get('custom', {})
            url = recurso['secure_url']
            db.agregar_foto({
                'nombre_archivo': recurso['public_id'],
                'nombre_original': ctx.get('nombre_original', recurso['public_id']),
                'ruta': url,
                'thumbnail': _thumbnail_url(url),
                'subido_por': ctx.get('subido_por', 'Invitado'),
                'descripcion': ctx.get('descripcion', ''),
            })
            importadas += 1

        cursor = resultado.get('next_cursor')
        if not cursor:
            break

    return importadas


_indice_recuperado = False


def _recuperar_indice_si_hace_falta():
    """
    Render recicla el contenedor y se lleva puesto el SQLite. Si la galería
    aparece vacía pero Cloudinary tiene fotos, la reconstruimos sola una vez.
    Sin esto, un reinicio en plena fiesta borraría el álbum de la pantalla.
    """
    global _indice_recuperado
    if _indice_recuperado or not CLOUDINARY_ENABLED:
        return []
    _indice_recuperado = True
    try:
        importadas = _sincronizar_desde_cloudinary()
        app.logger.info('Índice reconstruido desde Cloudinary: %s fotos', importadas)
    except Exception:
        app.logger.exception('No se pudo reconstruir el índice desde Cloudinary')
        return []
    return db.get_fotos()


@app.route('/admin/sync-from-cloudinary')
def sync_from_cloudinary():
    """Reconstrucción manual del índice. Protegida con ?secret=<ADMIN_SECRET>."""
    if not ADMIN_SECRET or request.args.get('secret') != ADMIN_SECRET:
        return jsonify({'error': 'Forbidden'}), 403
    if not CLOUDINARY_ENABLED:
        return jsonify({'error': 'Cloudinary no configurado'}), 400

    try:
        return jsonify({'success': True, 'imported': _sincronizar_desde_cloudinary()})
    except Exception as e:
        app.logger.exception('Error sincronizando desde Cloudinary')
        return jsonify({'error': str(e)}), 500


# ── Archivos locales (sólo desarrollo) ────────────────────────────────────────

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=bool(os.environ.get('FLASK_DEBUG')),
            host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
