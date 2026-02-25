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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
    return render_template('invitados/fotos.html', wedding=WEDDING_DATA)

@app.route('/galeria')
def galeria():
    """Galería de fotos"""
    fotos = db.get_fotos()
    return render_template('invitados/galeria.html', wedding=WEDDING_DATA, fotos=fotos)

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

@app.route('/api/fotos/upload', methods=['POST'])
def api_upload_foto():
    """API para subir foto"""
    try:
        if 'foto' not in request.files:
            return jsonify({'success': False, 'message': 'No se envió ninguna foto'}), 400
        
        file = request.files['foto']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"{timestamp}_{filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
            file.save(filepath)
            
            try:
                # Comprimir y redimensionar imagen
                img = Image.open(filepath)
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                img.save(filepath, optimize=True, quality=85)
                
                # Crear thumbnail
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', nombre_archivo)
                img.save(thumbnail_path, optimize=True, quality=80)
                thumbnail_rel = f"uploads/thumbnails/{nombre_archivo}"
            except Exception as e:
                print(f"Error creando thumbnail: {e}")
                thumbnail_rel = f"uploads/{nombre_archivo}"
            
            subido_por = request.form.get('nombre', 'Invitado')
            descripcion = request.form.get('descripcion', '')
            
            foto_id = db.agregar_foto({
                'nombre_archivo': nombre_archivo,
                'nombre_original': file.filename,
                'ruta': f"uploads/{nombre_archivo}",
                'thumbnail': thumbnail_rel,
                'subido_por': subido_por,
                'descripcion': descripcion
            })
            
            return jsonify({
                'success': True,
                'message': 'Foto subida correctamente',
                'id': foto_id,
                'filename': nombre_archivo
            })
        
        return jsonify({'success': False, 'message': 'Tipo de archivo no permitido'}), 400
    
    except Exception as e:
        print(f"Error en upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error al subir foto: {str(e)}'}), 500

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Servir archivos subidos"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
