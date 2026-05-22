import os
import zipfile
import shutil
import uuid
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__, 
            template_folder='.', 
            static_folder='.',
            static_url_path='') 

# Seguridad: Límite de 16MB por archivo
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

CARPETA_SUBIDAS = 'uploads'
CARPETA_PROCESADOS = 'processed'
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)
os.makedirs(CARPETA_PROCESADOS, exist_ok=True)

# Organización detallada solicitada:
MAPA_EXTENSIONES = {
    # Documentos
    '.pdf': 'PDFs',
    '.docx': 'Documentos_Word',
    '.doc': 'Documentos_Word',
    '.xlsx': 'Excel',
    '.pptx': 'PowerPoint',
    '.ppt': 'PowerPoint',
    '.txt': 'Notas_Texto',
    
    # Multimedia
    '.jpg': 'Fotos_JPG',
    '.png': 'Fotos_PNG',
    '.mp3': 'Audio_MP3',
    '.wav': 'Audio_Música',
    '.mp4': 'Videos',
    
    # Otros
    '.exe': 'Instaladores_EXE',
    '.zip': 'Comprimidos_ZIP'
}

@app.errorhandler(413)
def archivo_muy_grande(e):
    return "Error: El archivo es demasiado pesado (Máximo 16MB)", 413

def organizar_archivos_extraidos(ruta_temporal):
    """Recorre la carpeta extraída y mueve archivos a sus carpetas por extensión"""
    for raiz, _, archivos in os.walk(ruta_temporal):
        for nombre in archivos:
            _, ext = os.path.splitext(nombre)
            ext = ext.lower()
            
            if ext in MAPA_EXTENSIONES:
                nombre_carpeta = MAPA_EXTENSIONES[ext]
                ruta_destino = os.path.join(ruta_temporal, nombre_carpeta)
                os.makedirs(ruta_destino, exist_ok=True)
                
                ruta_original = os.path.join(raiz, nombre)
                # Solo movemos si el archivo no está ya en la carpeta de destino
                if raiz != ruta_destino:
                    shutil.move(ruta_original, os.path.join(ruta_destino, nombre))

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/organizar', methods=['POST'])
def gestionar_organizacion():
    if 'archivo_zip' not in request.files:
        return "Error: No se encontró el archivo en la petición", 400
    
    archivo = request.files['archivo_zip']
    if archivo and archivo.filename.endswith('.zip'):
        nombre_seguro = secure_filename(archivo.filename)
        id_unico = str(uuid.uuid4())[:8]
        ruta_zip = os.path.join(CARPETA_SUBIDAS, f"{id_unico}_{nombre_seguro}")
        archivo.save(ruta_zip)

        ruta_extraccion = os.path.join(CARPETA_SUBIDAS, f"{id_unico}_extraido")
        
        try:
            with zipfile.ZipFile(ruta_zip, 'r') as ref_zip:
                if ref_zip.testzip() is not None:
                    return "Error: El archivo ZIP parece estar corrupto", 400
                ref_zip.extractall(ruta_extraccion)

            # Ejecutar la lógica de organización personalizada
            organizar_archivos_extraidos(ruta_extraccion)

            nombre_salida = f"organizado_{id_unico}_{nombre_seguro}"
            ruta_final = os.path.join(CARPETA_PROCESADOS, nombre_salida)
            shutil.make_archive(ruta_final.replace('.zip', ''), 'zip', ruta_extraccion)

            # Limpieza de archivos temporales
            shutil.rmtree(ruta_extraccion)
            os.remove(ruta_zip)
            
            return send_file(ruta_final, as_attachment=True)
        
        except Exception as e:
            if os.path.exists(ruta_extraccion): shutil.rmtree(ruta_extraccion)
            return f"Error crítico durante el procesamiento: {str(e)}", 500
    
    return "Error: Formato no permitido. Debe subir un archivo .zip", 400

if __name__ == '__main__':
    app.run(debug=True)