# app_flask.py
from flask import Flask, render_template, request, send_file, jsonify
import os
from werkzeug.utils import secure_filename
import base64
import cv2

# Importar nuestro procesador desde main.py
from main import SOATProcessor

# Agregar datetime para timestamps
import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Instancia del procesador SOAT
processor = SOATProcessor()

def log_with_timestamp(level: str, message: str):
    """Logging básico para producción"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if level in ['ERROR', 'WARNING']:
        print(f"[{timestamp}] [{level}] {message}")

@app.route('/')
def index():
    """Página principal con el formulario"""
    return render_template('index.html')

@app.route('/procesar_soat', methods=['POST'])
def procesar_soat():
    """Procesa el SOAT con el monto ingresado"""
    try:
        # Recibir datos del formulario
        archivo_pdf = request.files.get('pdf_file')
        monto = request.form.get('monto', '').strip()
        tipo_soat = request.form.get('tipo_soat')
        identificador = request.form.get('identificador', '').strip()
        
        # Guardar identificador globalmente para las descargas
        # ultimo_identificador = identificador # Eliminado
        
        # Parámetros opcionales
        aplicar_mejoras = request.form.get('aplicar_mejoras', 'true').lower() == 'true'
        factor_brillo = float(request.form.get('factor_brillo', '1.15'))
        dpi_conversion = int(request.form.get('dpi', '300'))
        generar_pdf = request.form.get('generar_pdf', 'true').lower() == 'true'
        
        # Validaciones básicas
        if not archivo_pdf:
            return jsonify({'error': 'No se subió ningún archivo PDF'}), 400
            
        if not monto:
            return jsonify({'error': 'Debe ingresar un monto'}), 400
            
        if not tipo_soat or tipo_soat not in ['protecta', 'positiva']:
            return jsonify({'error': 'Debe seleccionar el tipo de SOAT (Protecta o Positiva)'}), 400
        
        # Validar que el monto sea un número válido
        if not processor.validar_numero(monto):
            return jsonify({'error': 'El monto ingresado no es válido. Use solo números y decimales (ej: 170.00)'}), 400
        
        # Validar parámetros de mejora
        if factor_brillo < 0.5 or factor_brillo > 2.0:
            factor_brillo = 1.15
            
        if dpi_conversion < 150 or dpi_conversion > 600:
            dpi_conversion = 300
        
        # Guardar archivo PDF temporalmente
        pdf_filename = secure_filename(archivo_pdf.filename)
        pdf_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{pdf_filename}")
        
        try:
            archivo_pdf.save(pdf_temp_path)
        except Exception as e:
            return jsonify({'error': f'Error guardando archivo PDF: {str(e)}'}), 500
        
        # Verificar que el archivo se guardó correctamente
        if not os.path.exists(pdf_temp_path):
            return jsonify({'error': 'Error guardando archivo PDF'}), 500
        
        # Actualizar archivo PDF correspondiente
        if not processor.actualizar_archivo_pdf(tipo_soat, pdf_temp_path):
            return jsonify({'error': f'No se pudo actualizar el archivo {tipo_soat}. Verifique que el PDF sea válido.'}), 500
        
        # Generar nombre de archivo usando SOLO el identificador
        if identificador:
            # Limpiar identificador para usar como nombre de archivo
            identificador_limpio = "".join(c for c in identificador if c.isalnum() or c in "._-")
            resultado_filename = f"{identificador_limpio}.jpg"
        else:
            # Si no hay identificador, usar formato original
            resultado_filename = f"resultado_{tipo_soat}_{monto}_{pdf_filename.replace('.pdf', '.jpg')}"
        
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], resultado_filename)
        
        resultado = processor.procesar_soat_con_digitos(
            tipo_soat=tipo_soat,
            numero=monto,
            archivo_salida=resultado_path,
            aplicar_mejoras=aplicar_mejoras,
            factor_brillo=factor_brillo,
            dpi_conversion=dpi_conversion,
            redimensionar_final=True,
            ancho_final=1694,
            alto_final=3300,
            generar_pdf=True
        )
        
        # Limpiar archivo temporal
        try:
            os.remove(pdf_temp_path)
        except:
            pass
        
        if resultado['success']:
            # Obtener la imagen resultado del procesamiento
            imagen_resultado = resultado['imagen_resultado']
            
            # Guardar la imagen en el servidor
            cv2.imwrite(resultado_path, imagen_resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Convertir la imagen a base64 para mostrar en el frontend
            _, buffer = cv2.imencode('.jpg', imagen_resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Información del procesamiento
            info_procesamiento = {
                'mejoras_aplicadas': resultado.get('mejoras_aplicadas', False),
                'factor_brillo_usado': factor_brillo,
                'dpi_usado': dpi_conversion,
                'imagen_origen': resultado.get('imagen_origen', 'descompuesto en dígitos con posiciones fijas'),
                'total_digitos': resultado.get('total_digitos', 0),
                'digitos_procesados': resultado.get('digitos', []),
                'posiciones_utilizadas': resultado.get('posiciones_utilizadas', {}),
                'pdf_generado': resultado.get('archivo_pdf') is not None
            }
            
            return jsonify({
                'success': True,
                'imagen_resultado': f"data:image/jpeg;base64,{img_base64}",
                'message': resultado['mensaje'],
                'tipo_soat': resultado['tipo_soat'],
                'monto': resultado['numero'],
                'empresa': resultado['tipo_soat'].upper(),
                'digitos': resultado.get('digitos', []),
                'total_digitos': resultado.get('total_digitos', 0),
                'imagenes_pegadas': resultado.get('imagenes_pegadas', []),
                'posiciones_utilizadas': resultado.get('posiciones_utilizadas', {}),
                'dimensiones_finales': resultado.get('dimensiones_finales', 'N/A'),
                'archivo_resultado': resultado_filename,
                'archivo_pdf': resultado.get('archivo_pdf'),
                'pdf_disponible': resultado.get('archivo_pdf') is not None,
                'info_procesamiento': info_procesamiento
            })
        else:
            return jsonify({'error': resultado['error']}), 400
        
    except ValueError as ve:
        return jsonify({'error': f'Error en los parámetros: {str(ve)}'}), 400
    except Exception as e:
        log_with_timestamp("ERROR", f"Error del servidor: {str(e)}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/procesar_soat_sin_monto', methods=['POST'])
def procesar_soat_sin_monto():
    """Procesa el SOAT SIN monto"""
    try:
        # Recibir datos del formulario
        archivo_pdf = request.files.get('pdf_file')
        tipo_soat = request.form.get('tipo_soat')
        identificador = request.form.get('identificador', '').strip()
        
        # Guardar identificador globalmente para las descargas
        # ultimo_identificador = identificador # Eliminado
        
        # Parámetros opcionales
        aplicar_mejoras = request.form.get('aplicar_mejoras', 'true').lower() == 'true'
        factor_brillo = float(request.form.get('factor_brillo', '1.3'))
        dpi_conversion = int(request.form.get('dpi', '300'))
        generar_pdf = request.form.get('generar_pdf', 'true').lower() == 'true'
        
        # Validaciones básicas
        if not archivo_pdf:
            return jsonify({'error': 'No se subió ningún archivo PDF'}), 400
            
        if not tipo_soat or tipo_soat not in ['protecta', 'positiva']:
            return jsonify({'error': 'Debe seleccionar el tipo de SOAT (Protecta o Positiva)'}), 400
        
        # Validar parámetros de mejora
        if factor_brillo < 0.5 or factor_brillo > 2.0:
            factor_brillo = 1.3
            
        if dpi_conversion < 150 or dpi_conversion > 600:
            dpi_conversion = 300
        
        # Guardar archivo PDF temporalmente
        pdf_filename = secure_filename(archivo_pdf.filename)
        pdf_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{pdf_filename}")
        archivo_pdf.save(pdf_temp_path)
        
        # Actualizar archivo PDF correspondiente
        if not processor.actualizar_archivo_pdf(tipo_soat, pdf_temp_path):
            return jsonify({'error': f'No se pudo actualizar el archivo {tipo_soat}. Verifique que el PDF sea válido.'}), 500
        
        # Generar nombre de archivo usando SOLO el identificador
        if identificador:
            # Limpiar identificador para usar como nombre de archivo
            identificador_limpio = "".join(c for c in identificador if c.isalnum() or c in "._-")
            resultado_filename = f"{identificador_limpio}.jpg"
        else:
            # Si no hay identificador, usar formato original
            resultado_filename = f"resultado_{tipo_soat}_SIN_MONTO_{pdf_filename.replace('.pdf', '.jpg')}"
        
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], resultado_filename)
        
        resultado = processor.procesar_soat_sin_monto(
            tipo_soat=tipo_soat,
            archivo_salida=resultado_path,
            aplicar_mejoras=aplicar_mejoras,
            factor_brillo=factor_brillo,
            dpi_conversion=dpi_conversion,
            redimensionar_final=True,
            ancho_final=1694,
            alto_final=3300,
            generar_pdf=True
        )
        
        # Limpiar archivo temporal
        try:
            os.remove(pdf_temp_path)
        except:
            pass
        
        if resultado['success']:
            # Obtener la imagen resultado del procesamiento
            imagen_resultado = resultado['imagen_resultado']
            
            # Convertir la imagen a base64 para mostrar en el frontend
            _, buffer = cv2.imencode('.jpg', imagen_resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Información del procesamiento
            info_procesamiento = {
                'mejoras_aplicadas': resultado.get('mejoras_aplicadas', False),
                'factor_brillo_usado': factor_brillo,
                'dpi_usado': dpi_conversion,
                'imagen_origen': resultado.get('imagen_origen', 'sin-monto.jpg (posición fija)'),
                'posicion_pegado': resultado.get('posicion_pegado', 'N/A'),
                'pdf_generado': resultado.get('archivo_pdf') is not None
            }
            
            return jsonify({
                'success': True,
                'imagen_resultado': f"data:image/jpeg;base64,{img_base64}",
                'message': resultado['mensaje'],
                'tipo_soat': resultado['tipo_soat'],
                'monto': 'SIN-MONTO',
                'empresa': resultado['tipo_soat'].upper(),
                'dimensiones_finales': resultado.get('dimensiones_finales', 'N/A'),
                'archivo_resultado': resultado_filename,
                'archivo_pdf': resultado.get('archivo_pdf'),
                'pdf_disponible': resultado.get('archivo_pdf') is not None,
                'info_procesamiento': info_procesamiento
            })
        else:
            return jsonify({'error': resultado['error']}), 400
        
    except ValueError as ve:
        return jsonify({'error': f'Error en los parámetros: {str(ve)}'}), 400
    except Exception as e:
        log_with_timestamp("ERROR", f"Error del servidor: {str(e)}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/descargar_jpg')
def descargar_jpg():
    """Descargar el archivo SOAT procesado en formato JPG más reciente"""
    try:
        # Buscar archivos JPG que empiecen con identificador (nuevo formato)
        archivos_jpg_identificador = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                                    if not f.startswith('resultado_') and f.endswith('.jpg')]
        
        # Si no hay archivos con identificador, buscar archivos con formato anterior
        if not archivos_jpg_identificador:
            archivos_jpg_identificador = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                                        if f.startswith('resultado_') and f.endswith('.jpg')]
        
        if not archivos_jpg_identificador:
            return "No hay archivos JPG procesados disponibles para descargar", 404
        
        archivo_mas_reciente = max(archivos_jpg_identificador, 
                                 key=lambda x: os.path.getctime(os.path.join(app.config['UPLOAD_FOLDER'], x)))
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo_mas_reciente)
        
        if os.path.exists(resultado_path):
            # Extraer el identificador del nombre del archivo
            if archivo_mas_reciente.startswith('resultado_'):
                # Formato anterior: resultado_protecta_170_archivo.jpg
                nombre_descarga = archivo_mas_reciente
            else:
                # Nuevo formato: identificador.jpg
                nombre_descarga = archivo_mas_reciente
            
            return send_file(resultado_path, as_attachment=True, download_name=nombre_descarga)
        return "Archivo JPG no encontrado", 404
        
    except Exception as e:
        log_with_timestamp("ERROR", f"Error descargando archivo JPG: {str(e)}")
        return f"Error descargando archivo JPG: {str(e)}", 500

@app.route('/descargar_pdf')
def descargar_pdf():
    """Descargar el archivo SOAT procesado en formato PDF más reciente"""
    try:
        # Buscar archivos PDF que empiecen con identificador (nuevo formato)
        archivos_pdf_identificador = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                                    if not f.startswith('resultado_') and f.endswith('.pdf')]
        
        # Si no hay archivos con identificador, buscar archivos con formato anterior
        if not archivos_pdf_identificador:
            archivos_pdf_identificador = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                                        if f.startswith('resultado_') and f.endswith('.pdf')]
        
        if not archivos_pdf_identificador:
            return "No hay archivos PDF procesados disponibles para descargar", 404
        
        archivo_mas_reciente = max(archivos_pdf_identificador, 
                                 key=lambda x: os.path.getctime(os.path.join(app.config['UPLOAD_FOLDER'], x)))
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo_mas_reciente)
        
        if os.path.exists(resultado_path):
            # Extraer el identificador del nombre del archivo
            if archivo_mas_reciente.startswith('resultado_'):
                # Formato anterior: resultado_protecta_170_archivo.pdf
                nombre_descarga = archivo_mas_reciente
            else:
                # Nuevo formato: identificador.pdf
                nombre_descarga = archivo_mas_reciente
            
            return send_file(resultado_path, as_attachment=True, download_name=nombre_descarga)
        return "Archivo PDF no encontrado", 404
        
    except Exception as e:
        log_with_timestamp("ERROR", f"Error descargando archivo PDF: {str(e)}")
        return f"Error descargando archivo PDF: {str(e)}", 500

@app.route('/restaurar_archivos', methods=['POST'])
def restaurar_archivos():
    """Restaurar archivos PDF originales desde backups"""
    try:
        resultado = processor.restaurar_archivos_backup()
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        log_with_timestamp("ERROR", f"Error restaurando archivos: {str(e)}")
        return jsonify({'error': f'Error restaurando archivos: {str(e)}'}), 500

def obtener_ip_local():
    """Obtiene la IP local de la máquina"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def mostrar_informacion_acceso():
    """Muestra las formas de acceso al servidor"""
    ip_local = obtener_ip_local()
    
    print("\n" + "="*60)
    print("EDITOR SOAT - SERVIDOR FLASK INICIADO")
    print("="*60)
    print(f"[LOCAL] Acceso Local:")
    print(f"   -> http://localhost:5000")
    print(f"   -> http://127.0.0.1:5000")
    print(f"")
    print(f"[RED] Acceso Red Local (misma red):")
    print(f"   -> http://{ip_local}:5000")
    print("="*60)
    print("\n")

if __name__ == '__main__':
    # Mostrar información de acceso
    mostrar_informacion_acceso()
    
    # Iniciar servidor Flask para producción
    try:
        print("Iniciando servidor Flask en puerto 5000...")
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario")
    except Exception as e:
        print(f"Error iniciando servidor: {e}")
        