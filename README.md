# Analizador de Autenticidad de Imágenes

Un sistema completo para analizar metadatos de imágenes y determinar su autenticidad mediante inteligencia artificial.

## Características Principales

### 🖼️ Carga de Imágenes
- **Carga múltiple**: Sube varias imágenes simultáneamente
- **Formatos soportados**: JPG, JPEG, PNG
- **Tamaño máximo**: Hasta 50MB en total
- **Interfaz intuitiva**: Arrastra y suelta o selecciona archivos

### 🔍 Análisis Avanzado
- **Extracción de metadatos**: EXIF, GPS, información de cámara
- **Detección de edición**: Identifica software de manipulación
- **Verificación técnica**: Consistencia entre metadatos y capacidades del dispositivo
- **Modelo IA**: Utiliza DeepSeek LLM (7B) para análisis forense

### 📊 Resultados
- **Informe detallado**: Análisis individual por imagen
- **Puntuación de confianza**: 0-100% de autenticidad
- **Conclusión clara**: Auténtica/Sospechosa/Manipulada
- **Historial completo**: Accede a todos los análisis previos

### 🚀 Tecnologías Utilizadas
- **Backend**: Python con Flask
- **Procesamiento de imágenes**: Pillow, piexif
- **Inteligencia Artificial**: Transformers de HuggingFace
- **Interfaz**: HTML5, CSS3, JavaScript

## Requisitos del Sistema

### 📦 Dependencias

pip install flask pillow piexif transformers torch python-dateutil

### Iniciar la aplicación:

python app.py
Acceder a la interfaz:
Abre tu navegador en http://localhost:5000
