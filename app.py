#!/usr/bin/env python3
"""
App pública para invitados - Solo subir y ver fotos
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
from database import CasamientoDatabase

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB para múltiples fotos

# Usar /tmp en producción (Render) o static/uploads en local
if os.environ.get('RENDER'):
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
else:
    app.config['UPLOAD_FOLDER'] = 'static/uploads'

app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif'}

# Crear carpetas de uploads si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)

db = CasamientoDatabase()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Datos del casamiento (solo info básica)
WEDDING_DATA = {
    'novia': 'Katherine',
    'novio': 'Ariel',
    'fecha': '19 de Diciembre 2026',
    'lugar': 'Basílica de Lourdes'
}

@app.route('/')
def index():
    """Página principal - Subir fotos"""
    return render_template('fotos.html', wedding=WEDDING_DATA)

@app.route('/galeria')
def galeria():
    """Galería de fotos"""
    fotos = db.get_fotos()
    return render_template('galeria.html', wedding=WEDDING_DATA, fotos=fotos)

@app.route('/qr-page')
def qr_page():
    """Página del código QR"""
    return render_template('qr.html', wedding=WEDDING_DATA)

@app.route('/qr')
def qr_code():
    """Generar código QR"""
    import qrcode
    import io
    
    url = request.host_url
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    from flask import send_file
    return send_file(img_io, mimetype='image/png')

@app.route('/api/fotos', methods=['GET'])
def api_get_fotos():
    """API para obtener fotos"""
    fotos = db.get_fotos()
    return jsonify(fotos)

def procesar_foto(file, subido_por, descripcion):
    """Procesar y guardar una foto"""
    filename = secure_filename(file.filename)
    import uuid
    nombre_archivo = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
    file.save(filepath)
    
    try:
        img = Image.open(filepath)
        # Convertir a RGB si es necesario (HEIC, PNG con transparencia, etc.)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        img.save(filepath, 'JPEG', optimize=True, quality=85)
        
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', nombre_archivo)
        img.save(thumbnail_path, 'JPEG', optimize=True, quality=80)
        thumbnail_rel = f"uploads/thumbnails/{nombre_archivo}"
    except Exception as e:
        print(f"Error procesando imagen: {e}")
        thumbnail_rel = f"uploads/{nombre_archivo}"
    
    foto_id = db.agregar_foto({
        'nombre_archivo': nombre_archivo,
        'nombre_original': file.filename,
        'ruta': f"uploads/{nombre_archivo}",
        'thumbnail': thumbnail_rel,
        'subido_por': subido_por,
        'descripcion': descripcion
    })
    
    return foto_id

@app.route('/api/fotos/upload', methods=['POST'])
def api_upload_foto():
    """API para subir una o múltiples fotos"""
    try:
        files = request.files.getlist('fotos')
        
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': 'No se enviaron fotos'}), 400
        
        subido_por = request.form.get('nombre', 'Invitado')
        descripcion = request.form.get('descripcion', '')
        
        subidas = []
        errores = []
        
        for file in files:
            if file.filename == '':
                continue
            if not allowed_file(file.filename):
                errores.append(f'{file.filename}: tipo no permitido')
                continue
            try:
                foto_id = procesar_foto(file, subido_por, descripcion)
                subidas.append(foto_id)
            except Exception as e:
                errores.append(f'{file.filename}: {str(e)}')
        
        if not subidas:
            return jsonify({'success': False, 'message': 'No se pudo subir ninguna foto'}), 400
        
        msg = f'{"¡" if not errores else ""}{len(subidas)} foto{"s" if len(subidas) > 1 else ""} subida{"s" if len(subidas) > 1 else ""} correctamente'
        return jsonify({'success': True, 'message': msg, 'subidas': len(subidas), 'errores': errores})
    
    except Exception as e:
        print(f"Error en upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Servir archivos subidos"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
