import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import piexif
from transformers import pipeline
from datetime import datetime
import re
from dateutil import parser as date_parser
from concurrent.futures import ThreadPoolExecutor

# Configuración de la aplicación Flask
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png'}
app.config['MAX_PARALLEL_PROCESSES'] = 4  # Número máximo de imágenes a procesar simultáneamente

# Clase analizadora mejorada para múltiples imágenes
class AnalizadorImagenesWeb:
    def __init__(self):
        self.modelo = "deepseek-ai/deepseek-llm-7b-chat"
        try:
            self.pipe = pipeline(
                "text-generation",
                model=self.modelo,
                device_map="auto",
                torch_dtype="auto"
            )
        except Exception as e:
            print(f"Error cargando el modelo: {str(e)}")
            self.pipe = None
        
        self.patrones_edicion = [
            r"photoshop|adobe|lightroom|gimp|paint\s?shop|corel|after\s?effects",
            r"editado|manipulado|retocado|alterado|clonado|modificado"
        ]
        
        self.camaras_conocidas = {
            "Canon EOS 5D Mark IV": {"max_res": (6720, 4480), "max_iso": 32000},
            "Nikon D850": {"max_res": (8256, 5504), "max_iso": 102400},
            "SONY ILCE-7M4": {"max_res": (7008, 4672), "max_iso": 204800}
        }

    def extraer_metadatos(self, file_path):
        """Extrae metadatos usando Pillow y piexif"""
        try:
            img = Image.open(file_path)
            metadatos = {
                "ImageWidth": img.width,
                "ImageHeight": img.height,
                "Format": img.format,
                "Filename": os.path.basename(file_path),
                "FilePath": file_path
            }
            
            if 'exif' in img.info:
                try:
                    exif_dict = piexif.load(img.info['exif'])
                    for ifd in ("0th", "Exif", "GPS", "1st"):
                        if ifd in exif_dict:
                            for tag, value in exif_dict[ifd].items():
                                if tag in piexif.TAGS[ifd]:
                                    tag_name = piexif.TAGS[ifd][tag]["name"]
                                    try:
                                        if isinstance(value, bytes):
                                            value = value.decode(errors='ignore')
                                        metadatos[tag_name] = value
                                    except:
                                        metadatos[tag_name] = str(value)
                except Exception as exif_error:
                    metadatos["ExifError"] = str(exif_error)
            
            return metadatos
        except Exception as e:
            raise ValueError(f"Error al procesar imagen: {str(e)}")

    def analizar_autenticidad(self, metadatos):
        """Realiza análisis básico y devuelve resultados simplificados"""
        if not self.pipe:
            return {
                'error': 'Modelo no disponible',
                'metadatos': metadatos
            }
        
        try:
            # Análisis técnico básico
            hallazgos = []
            if 'Software' in metadatos:
                software = str(metadatos['Software']).lower()
                for patron in self.patrones_edicion:
                    if re.search(patron, software):
                        hallazgos.append(f"Software de edición detectado: {software}")
                        break
            
            # Crear prompt para el LLM
            prompt = f"""Analiza los metadatos de esta imagen y determina su autenticidad.
            
            Metadatos principales:
            - Dispositivo: {metadatos.get('Make', 'Desconocido')} {metadatos.get('Model', 'Desconocido')}
            - Fecha: {metadatos.get('DateTimeOriginal', 'No disponible')}
            - Resolución: {metadatos.get('ImageWidth', '?')}x{metadatos.get('ImageHeight', '?')}
            - Software: {metadatos.get('Software', 'No especificado')}
            
            Hallazgos técnicos: {', '.join(hallazgos) or 'Ninguno'}
            
            Proporciona un análisis conciso (3-5 oraciones) y una conclusión (Auténtica/Sospechosa/Manipulada)."""
            
            # Generar respuesta
            respuesta = self.pipe(
                prompt,
                max_new_tokens=300,
                temperature=0.3,
                do_sample=False
            )[0]['generated_text']
            
            return {
                'metadatos': metadatos,
                'analisis': respuesta,
                'hallazgos': hallazgos,
                'filename': metadatos['Filename'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'metadatos': metadatos,
                'filename': metadatos['Filename'],
                'timestamp': datetime.now().isoformat()
            }

    def procesar_lote(self, file_paths):
        """Procesa múltiples imágenes en paralelo"""
        with ThreadPoolExecutor(max_workers=app.config['MAX_PARALLEL_PROCESSES']) as executor:
            resultados = list(executor.map(self.procesar_imagen, file_paths))
        return resultados

    def procesar_imagen(self, file_path):
        """Procesa una sola imagen y devuelve resultados"""
        try:
            metadatos = self.extraer_metadatos(file_path)
            return self.analizar_autenticidad(metadatos)
        except Exception as e:
            return {
                'error': str(e),
                'filename': os.path.basename(file_path),
                'timestamp': datetime.now().isoformat()
            }

# Crear directorios necesarios
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Instanciar el analizador
analizador = AnalizadorImagenesWeb()

# Funciones de ayuda
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Rutas de la aplicación Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        flash('No se seleccionaron archivos')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files[]')
    if len(files) == 0 or files[0].filename == '':
        flash('No se seleccionaron archivos válidos')
        return redirect(url_for('index'))
    
    # Filtrar archivos válidos
    valid_files = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            valid_files.append(filepath)
    
    if not valid_files:
        flash('Ningún archivo tenía un formato válido (solo JPG, JPEG, PNG)')
        return redirect(url_for('index'))
    
    # Procesar imágenes en paralelo
    resultados = analizador.procesar_lote(valid_files)
    
    # Guardar resultados
    resultados_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resultados.json')
    
    if os.path.exists(resultados_path):
        with open(resultados_path, 'r') as f:
            resultados_existentes = json.load(f)
    else:
        resultados_existentes = []
    
    resultados_existentes.extend(resultados)
    
    with open(resultados_path, 'w') as f:
        json.dump(resultados_existentes, f, indent=2)
    
    return render_template('resultados.html', resultados=resultados)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/all_results')
def ver_resultados():
    resultados_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resultados.json')
    if os.path.exists(resultados_path):
        with open(resultados_path, 'r') as f:
            resultados = json.load(f)
        return render_template('all_results.html', resultados=resultados[::-1])  # Más recientes primero
    else:
        flash('No hay resultados disponibles')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
