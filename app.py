#!/usr/bin/env python3
"""
App pública para invitados - Solo subir y ver fotos
Fotos persistidas en Cloudinary; SQLite como índice local.
"""

import os
import uuid
from datetime import datetime
from io import BytesIO

import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from database import CasamientoDatabase

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Carpeta local solo para fallback en desarrollo sin Cloudinary
app.config['UPLOAD_FOLDER'] = '/tmp/uploads' if os.environ.get('RENDER') else 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── Cloudinary ────────────────────────────────────────────────────────────────
CLOUDINARY_ENABLED = bool(os.environ.get('CLOUDINARY_CLOUD_NAME'))

if CLOUDINARY_ENABLED:
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True,
    )

CLOUDINARY_FOLDER = 'casamiento-katherine-ariel'

db = CasamientoDatabase()

WEDDING_DATA = {
    'novia': 'Katherine',
    'novio': 'Ariel',
    'fecha': '19 de Diciembre 2026',
    'lugar': 'Basílica de Lourdes',
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def _thumbnail_url(cloudinary_url: str) -> str:
    """Genera una URL de thumbnail 400×400 a partir de la URL original de Cloudinary."""
    # Inserta la transformación justo después de /upload/
    return cloudinary_url.replace('/upload/', '/upload/w_400,h_400,c_fill,q_auto,f_auto/', 1)


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('fotos.html', wedding=WEDDING_DATA)


@app.route('/galeria')
def galeria():
    fotos = db.get_fotos()
    return render_template('galeria.html', wedding=WEDDING_DATA, fotos=fotos)


@app.route('/qr-page')
def qr_page():
    return render_template('qr.html', wedding=WEDDING_DATA)


@app.route('/qr')
def qr_code():
    import qrcode
    url = request.host_url
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    from flask import send_file
    return send_file(img_io, mimetype='image/png')


@app.route('/api/fotos', methods=['GET'])
def api_get_fotos():
    return jsonify(db.get_fotos())


# ── Upload ────────────────────────────────────────────────────────────────────

def _upload_to_cloudinary(file_bytes: bytes, original_filename: str,
                           subido_por: str, descripcion: str) -> dict:
    """Sube la imagen a Cloudinary y devuelve ruta + thumbnail."""
    public_id = f"{CLOUDINARY_FOLDER}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    result = cloudinary.uploader.upload(
        BytesIO(file_bytes),
        public_id=public_id,
        resource_type='image',
        overwrite=False,
        quality='auto',
        fetch_format='auto',
        context={
            'subido_por': subido_por,
            'descripcion': descripcion,
            'nombre_original': original_filename,
        },
    )

    ruta = result['secure_url']
    thumbnail = _thumbnail_url(ruta)
    return {'ruta': ruta, 'thumbnail': thumbnail, 'nombre_archivo': result['public_id']}


def _upload_local(file, subido_por: str, descripcion: str) -> dict:
    """Fallback: guarda la imagen localmente (desarrollo sin Cloudinary)."""
    from PIL import Image

    filename = secure_filename(file.filename)
    nombre_archivo = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
    file.save(filepath)

    try:
        img = Image.open(filepath)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        img.save(filepath, 'JPEG', optimize=True, quality=85)

        thumb_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails')
        os.makedirs(thumb_dir, exist_ok=True)
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        img.save(os.path.join(thumb_dir, nombre_archivo), 'JPEG', optimize=True, quality=80)
        thumbnail = f'uploads/thumbnails/{nombre_archivo}'
    except Exception as e:
        print(f'Error procesando imagen local: {e}')
        thumbnail = f'uploads/{nombre_archivo}'

    return {'ruta': f'uploads/{nombre_archivo}', 'thumbnail': thumbnail,
            'nombre_archivo': nombre_archivo}


def procesar_foto(file, subido_por: str, descripcion: str) -> int:
    """Procesa y persiste una foto; devuelve el ID en la BD local."""
    if CLOUDINARY_ENABLED:
        file_bytes = file.read()
        urls = _upload_to_cloudinary(file_bytes, file.filename, subido_por, descripcion)
    else:
        urls = _upload_local(file, subido_por, descripcion)

    return db.agregar_foto({
        'nombre_archivo': urls['nombre_archivo'],
        'nombre_original': file.filename,
        'ruta': urls['ruta'],
        'thumbnail': urls['thumbnail'],
        'subido_por': subido_por,
        'descripcion': descripcion,
    })


@app.route('/api/fotos/upload', methods=['POST'])
def api_upload_foto():
    try:
        files = request.files.getlist('fotos')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': 'No se enviaron fotos'}), 400

        subido_por  = request.form.get('nombre', 'Invitado')
        descripcion = request.form.get('descripcion', '')
        subidas, errores = [], []

        for file in files:
            if not file.filename:
                continue
            if not allowed_file(file.filename):
                errores.append(f'{file.filename}: tipo no permitido')
                continue
            try:
                subidas.append(procesar_foto(file, subido_por, descripcion))
            except Exception as e:
                print(f'Error subiendo {file.filename}: {e}')
                errores.append(f'{file.filename}: {str(e)}')

        if not subidas:
            return jsonify({'success': False, 'message': 'No se pudo subir ninguna foto'}), 400

        n = len(subidas)
        msg = f'{n} foto{"s" if n > 1 else ""} subida{"s" if n > 1 else ""} correctamente'
        return jsonify({'success': True, 'message': msg, 'subidas': n, 'errores': errores})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ── Sync: reconstruye SQLite desde Cloudinary ─────────────────────────────────

@app.route('/admin/sync-from-cloudinary')
def sync_from_cloudinary():
    """
    Reconstruye el índice SQLite a partir de las imágenes almacenadas en Cloudinary.
    Útil si el contenedor se reinicia y la BD local se pierde.
    Protegido con ?secret=<ADMIN_SECRET>.
    """
    secret = os.environ.get('ADMIN_SECRET', '')
    if secret and request.args.get('secret') != secret:
        return jsonify({'error': 'Forbidden'}), 403

    if not CLOUDINARY_ENABLED:
        return jsonify({'error': 'Cloudinary no configurado'}), 400

    try:
        # Borra la tabla y la vuelve a llenar
        conn = db.get_connection()
        conn.execute('DELETE FROM fotos')
        conn.commit()
        conn.close()

        imported = 0
        next_cursor = None

        while True:
            params = dict(type='upload', prefix=CLOUDINARY_FOLDER,
                          max_results=100, context=True)
            if next_cursor:
                params['next_cursor'] = next_cursor

            result = cloudinary.api.resources(**params)

            for resource in result.get('resources', []):
                ctx = resource.get('context', {}).get('custom', {})
                ruta = resource['secure_url']
                db.agregar_foto({
                    'nombre_archivo': resource['public_id'],
                    'nombre_original': ctx.get('nombre_original', resource['public_id']),
                    'ruta': ruta,
                    'thumbnail': _thumbnail_url(ruta),
                    'subido_por': ctx.get('subido_por', 'Invitado'),
                    'descripcion': ctx.get('descripcion', ''),
                })
                imported += 1

            next_cursor = result.get('next_cursor')
            if not next_cursor:
                break

        return jsonify({'success': True, 'imported': imported})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── Servir archivos locales (solo en desarrollo) ──────────────────────────────

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
