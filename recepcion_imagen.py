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
    """
    Función personalizada para logging con timestamp en Flask
    
    Args:
        level: Nivel del log (INFO, OK, ERROR, WARNING, DEBUG, SAVE)
        message: Mensaje a mostrar
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

@app.route('/')
def index():
    """Página principal con el formulario simplificado"""
    return render_template('index.html')

@app.route('/procesar_soat', methods=['POST'])
def procesar_soat():
    """Procesa el SOAT con el monto ingresado usando la nueva funcionalidad de dígitos con posiciones fijas"""
    try:
        log_with_timestamp("INFO", "=== INICIANDO PROCESAMIENTO SOAT ===")
        log_with_timestamp("INFO", "Iniciando procesamiento de SOAT con monto")
        
        # DEBUG: Mostrar todos los datos recibidos
        log_with_timestamp("DEBUG", f"Request method: {request.method}")
        log_with_timestamp("DEBUG", f"Request content type: {request.content_type}")
        log_with_timestamp("DEBUG", f"Request form keys: {list(request.form.keys())}")
        log_with_timestamp("DEBUG", f"Request files keys: {list(request.files.keys())}")
        
        # Recibir datos del formulario
        archivo_pdf = request.files.get('pdf_file')
        monto = request.form.get('monto', '').strip()
        tipo_soat = request.form.get('tipo_soat')
        
        log_with_timestamp("INFO", f"Datos recibidos - PDF: {archivo_pdf.filename if archivo_pdf else 'None'}, Monto: {monto}, Tipo: {tipo_soat}")
        
        # DEBUG: Verificar si el archivo PDF está presente
        if archivo_pdf:
            log_with_timestamp("DEBUG", f"Archivo PDF presente - Nombre: {archivo_pdf.filename}, Tamaño: {archivo_pdf.content_length if hasattr(archivo_pdf, 'content_length') else 'N/A'}")
        else:
            log_with_timestamp("ERROR", "No se recibió archivo PDF en la petición")
            return jsonify({'error': 'No se recibió archivo PDF en la petición'}), 400
        
        # Parámetros opcionales para mejoras
        aplicar_mejoras = request.form.get('aplicar_mejoras', 'true').lower() == 'true'
        factor_brillo = float(request.form.get('factor_brillo', '1.15'))
        dpi_conversion = int(request.form.get('dpi', '300'))
        generar_pdf = request.form.get('generar_pdf', 'true').lower() == 'true'
        
        log_with_timestamp("INFO", f"Parámetros - Mejoras: {aplicar_mejoras}, Brillo: {factor_brillo}, DPI: {dpi_conversion}, PDF: {generar_pdf}")
        
        # Validaciones básicas
        if not archivo_pdf:
            log_with_timestamp("ERROR", "No se subió ningún archivo PDF")
            return jsonify({'error': 'No se subió ningún archivo PDF'}), 400
            
        if not monto:
            log_with_timestamp("ERROR", "Debe ingresar un monto")
            return jsonify({'error': 'Debe ingresar un monto'}), 400
            
        if not tipo_soat or tipo_soat not in ['protecta', 'positiva']:
            log_with_timestamp("ERROR", "Debe seleccionar el tipo de SOAT (Protecta o Positiva)")
            return jsonify({'error': 'Debe seleccionar el tipo de SOAT (Protecta o Positiva)'}), 400
        
        # Validar que el monto sea un número válido
        if not processor.validar_numero(monto):
            log_with_timestamp("ERROR", f"El monto ingresado '{monto}' no es válido. Use solo números y decimales (ej: 170.00)")
            return jsonify({'error': 'El monto ingresado no es válido. Use solo números y decimales (ej: 170.00)'}), 400
        
        # Validar parámetros de mejora
        if factor_brillo < 0.5 or factor_brillo > 2.0:
            factor_brillo = 1.15  # Valor por defecto
            
        if dpi_conversion < 150 or dpi_conversion > 600:
            dpi_conversion = 300  # Valor por defecto
        
        # Guardar archivo PDF temporalmente
        pdf_filename = secure_filename(archivo_pdf.filename)
        pdf_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{pdf_filename}")
        log_with_timestamp("INFO", f"Guardando PDF temporal: {pdf_temp_path}")
        
        try:
            archivo_pdf.save(pdf_temp_path)
            log_with_timestamp("DEBUG", f"PDF guardado exitosamente en: {pdf_temp_path}")
        except Exception as e:
            log_with_timestamp("ERROR", f"Error guardando PDF: {str(e)}")
            return jsonify({'error': f'Error guardando archivo PDF: {str(e)}'}), 500
        
        # Verificar que el archivo se guardó correctamente
        if not os.path.exists(pdf_temp_path):
            log_with_timestamp("ERROR", f"El archivo PDF no se guardó correctamente en: {pdf_temp_path}")
            return jsonify({'error': 'Error guardando archivo PDF'}), 500
        
        log_with_timestamp("DEBUG", f"Archivo PDF verificado - Tamaño: {os.path.getsize(pdf_temp_path)} bytes")
        
        # Actualizar archivo PDF correspondiente
        log_with_timestamp("INFO", f"Actualizando archivo PDF para {tipo_soat}")
        if not processor.actualizar_archivo_pdf(tipo_soat, pdf_temp_path):
            log_with_timestamp("ERROR", f"No se pudo actualizar el archivo {tipo_soat}. Verifique que el PDF sea válido.")
            return jsonify({'error': f'No se pudo actualizar el archivo {tipo_soat}. Verifique que el PDF sea válido.'}), 500
        
        # Procesar SOAT con la nueva funcionalidad de dígitos
        resultado_filename = f"resultado_{tipo_soat}_{monto}_{pdf_filename.replace('.pdf', '.jpg')}"
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], resultado_filename)
        
        log_with_timestamp("INFO", f"Iniciando procesamiento con dígitos para {tipo_soat} - {monto}")
        
        # Usar la nueva función de procesamiento con dígitos y posiciones fijas
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
            generar_pdf=True  # Asegurar que esté en True
        )
        
        log_with_timestamp("INFO", f"Resultado del procesamiento: {resultado.get('success', False)}")
        
        # Limpiar archivo temporal
        try:
            os.remove(pdf_temp_path)
            log_with_timestamp("INFO", "Archivo temporal eliminado")
        except:
            pass  # No importa si no se puede eliminar
        
        if resultado['success']:
            log_with_timestamp("OK", f"SOAT procesado exitosamente: {resultado['mensaje']}")
            # Obtener la imagen resultado del procesamiento
            imagen_resultado = resultado['imagen_resultado']
            
            # Guardar la imagen en el servidor (para descarga)
            cv2.imwrite(resultado_path, imagen_resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Convertir la MISMA imagen a base64 para mostrar en el frontend
            _, buffer = cv2.imencode('.jpg', imagen_resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Información detallada del procesamiento
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
            
            log_with_timestamp("OK", "=== PROCESAMIENTO COMPLETADO EXITOSAMENTE ===")
            
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
                'archivo_pdf': resultado.get('archivo_pdf'),  # NUEVO: Ruta del PDF
                'pdf_disponible': resultado.get('archivo_pdf') is not None,  # NUEVO: Si PDF está disponible
                'info_procesamiento': info_procesamiento
            })
        else:
            log_with_timestamp("ERROR", f"Error procesando SOAT: {resultado['error']}")
            return jsonify({'error': resultado['error']}), 400
        
    except ValueError as ve:
        log_with_timestamp("ERROR", f"Error en los parámetros: {str(ve)}")
        return jsonify({'error': f'Error en los parámetros: {str(ve)}'}), 400
    except Exception as e:
        log_with_timestamp("ERROR", f"Error del servidor: {str(e)}")
        import traceback
        log_with_timestamp("ERROR", f"Traceback completo: {traceback.format_exc()}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/procesar_soat_sin_monto', methods=['POST'])
def procesar_soat_sin_monto():
    """Procesa el SOAT SIN monto - solo pega la imagen sin-monto.jpg"""
    try:
        log_with_timestamp("INFO", "Iniciando procesamiento de SOAT sin monto")
        # Recibir datos del formulario
        archivo_pdf = request.files.get('pdf_file')
        tipo_soat = request.form.get('tipo_soat')
        
        # Parámetros opcionales para mejoras
        aplicar_mejoras = request.form.get('aplicar_mejoras', 'true').lower() == 'true'
        factor_brillo = float(request.form.get('factor_brillo', '1.3'))
        dpi_conversion = int(request.form.get('dpi', '300'))
        generar_pdf = request.form.get('generar_pdf', 'true').lower() == 'true'
        
        # Validaciones básicas
        if not archivo_pdf:
            log_with_timestamp("ERROR", "No se subió ningún archivo PDF")
            return jsonify({'error': 'No se subió ningún archivo PDF'}), 400
            
        if not tipo_soat or tipo_soat not in ['protecta', 'positiva']:
            log_with_timestamp("ERROR", "Debe seleccionar el tipo de SOAT (Protecta o Positiva)")
            return jsonify({'error': 'Debe seleccionar el tipo de SOAT (Protecta o Positiva)'}), 400
        
        # Validar parámetros de mejora
        if factor_brillo < 0.5 or factor_brillo > 2.0:
            factor_brillo = 1.3  # Valor por defecto
            
        if dpi_conversion < 150 or dpi_conversion > 600:
            dpi_conversion = 300  # Valor por defecto
        
        # Guardar archivo PDF temporalmente
        pdf_filename = secure_filename(archivo_pdf.filename)
        pdf_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{pdf_filename}")
        archivo_pdf.save(pdf_temp_path)
        
        # Actualizar archivo PDF correspondiente
        if not processor.actualizar_archivo_pdf(tipo_soat, pdf_temp_path):
            log_with_timestamp("ERROR", f"No se pudo actualizar el archivo {tipo_soat}. Verifique que el PDF sea válido.")
            return jsonify({'error': f'No se pudo actualizar el archivo {tipo_soat}. Verifique que el PDF sea válido.'}), 500
        
        # Procesar SOAT SIN MONTO
        resultado_filename = f"resultado_{tipo_soat}_SIN_MONTO_{pdf_filename.replace('.pdf', '.jpg')}"
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], resultado_filename)
        
        # Usar la nueva función de procesamiento SIN MONTO
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
            pass  # No importa si no se puede eliminar
        
        if resultado['success']:
            log_with_timestamp("OK", f"SOAT sin monto procesado exitosamente: {resultado['mensaje']}")
            # Obtener la imagen resultado del procesamiento
            imagen_resultado = resultado['imagen_resultado']
            
            # Convertir la imagen a base64 para mostrar en el frontend
            _, buffer = cv2.imencode('.jpg', imagen_resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Información detallada del procesamiento
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
            log_with_timestamp("ERROR", f"Error procesando SOAT sin monto: {resultado['error']}")
            return jsonify({'error': resultado['error']}), 400
        
    except ValueError as ve:
        log_with_timestamp("ERROR", f"Error en los parámetros: {str(ve)}")
        return jsonify({'error': f'Error en los parámetros: {str(ve)}'}), 400
    except Exception as e:
        log_with_timestamp("ERROR", f"Error del servidor: {str(e)}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/listar_imagenes_disponibles')
def listar_imagenes_disponibles():
    """Lista todas las imágenes disponibles en el sistema con sus números"""
    try:
        imagenes = processor.listar_imagenes_disponibles()
        
        if imagenes:
            return jsonify({
                'success': True,
                'imagenes': imagenes,
                'total': len(imagenes),
                'numeros_disponibles': list(set([num for img in imagenes for num in img['numeros']]))
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No se encontraron imágenes con números en el sistema',
                'imagenes': [],
                'total': 0,
                'numeros_disponibles': []
            })
            
    except Exception as e:
        log_with_timestamp("ERROR", f"Error listando imágenes: {str(e)}")
        return jsonify({'error': f'Error listando imágenes: {str(e)}'}), 500

@app.route('/validar_monto/<monto>')
def validar_monto(monto):
    """Valida si existe una imagen para el monto especificado"""
    try:
        # Validar formato del monto
        if not processor.validar_numero(monto):
            return jsonify({
                'success': False,
                'error': 'Formato de monto inválido'
            })
        
        # Buscar imagen para el monto
        imagen_encontrada = processor.buscar_imagen_por_numero(monto)
        
        if imagen_encontrada:
            return jsonify({
                'success': True,
                'monto_disponible': True,
                'imagen_encontrada': imagen_encontrada,
                'mensaje': f'Se encontró imagen para el monto {monto}'
            })
        else:
            # Obtener números disponibles
            imagenes = processor.listar_imagenes_disponibles()
            numeros_disponibles = list(set([num for img in imagenes for num in img['numeros']]))
            
            return jsonify({
                'success': True,
                'monto_disponible': False,
                'imagen_encontrada': None,
                'mensaje': f'No se encontró imagen para el monto {monto}',
                'numeros_disponibles': numeros_disponibles
            })
            
    except Exception as e:
        log_with_timestamp("ERROR", f"Error validando monto: {str(e)}")
        return jsonify({'error': f'Error validando monto: {str(e)}'}), 500

@app.route('/configuracion_mejoras')
def configuracion_mejoras():
    """Retorna la configuración disponible para mejoras de calidad"""
    return jsonify({
        'success': True,
        'factores_brillo': {
            'minimo': 0.5,
            'maximo': 2.0,
            'por_defecto': 1.15,
            'recomendado': 1.15
        },
        'metodos_calidad': {
            'bilateral': 'Filtro bilateral - Reduce ruido conservando bordes (recomendado)',
            'gaussian': 'Filtro gaussiano con máscara de enfoque',
            'unsharp': 'Máscara de enfoque agresiva'
        },
        'dpi_opciones': {
            'minimo': 150,
            'maximo': 600,
            'por_defecto': 300,
            'recomendado': 300
        }
    })

@app.route('/descargar_resultado')
def descargar_resultado():
    """Descargar el archivo SOAT procesado más reciente"""
    try:
        archivos_resultado = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                            if f.startswith('resultado_') and f.endswith('.jpg')]
        
        if not archivos_resultado:
            return "No hay archivos procesados disponibles para descargar", 404
        
        # Tomar el más reciente
        archivo_mas_reciente = max(archivos_resultado, 
                                 key=lambda x: os.path.getctime(os.path.join(app.config['UPLOAD_FOLDER'], x)))
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo_mas_reciente)
        
        if os.path.exists(resultado_path):
            return send_file(resultado_path, as_attachment=True, download_name=archivo_mas_reciente)
        return "Archivo no encontrado", 404
        
    except Exception as e:
        log_with_timestamp("ERROR", f"Error descargando archivo: {str(e)}")
        return f"Error descargando archivo: {str(e)}", 500

@app.route('/descargar_pdf')
def descargar_pdf():
    """Descargar el archivo SOAT procesado en formato PDF más reciente"""
    try:
        archivos_pdf = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                       if f.startswith('resultado_') and f.endswith('.pdf')]
        
        if not archivos_pdf:
            return "No hay archivos PDF procesados disponibles para descargar", 404
        
        # Tomar el más reciente
        archivo_mas_reciente = max(archivos_pdf, 
                                 key=lambda x: os.path.getctime(os.path.join(app.config['UPLOAD_FOLDER'], x)))
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo_mas_reciente)
        
        if os.path.exists(resultado_path):
            return send_file(resultado_path, as_attachment=True, download_name=archivo_mas_reciente)
        return "Archivo PDF no encontrado", 404
        
    except Exception as e:
        log_with_timestamp("ERROR", f"Error descargando archivo PDF: {str(e)}")
        return f"Error descargando archivo PDF: {str(e)}", 500

@app.route('/descargar_jpg')
def descargar_jpg():
    """Descargar el archivo SOAT procesado en formato JPG más reciente"""
    try:
        archivos_jpg = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                       if f.startswith('resultado_') and f.endswith('.jpg')]
        
        if not archivos_jpg:
            return "No hay archivos JPG procesados disponibles para descargar", 404
        
        # Tomar el más reciente
        archivo_mas_reciente = max(archivos_jpg, 
                                 key=lambda x: os.path.getctime(os.path.join(app.config['UPLOAD_FOLDER'], x)))
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo_mas_reciente)
        
        if os.path.exists(resultado_path):
            return send_file(resultado_path, as_attachment=True, download_name=archivo_mas_reciente)
        return "Archivo JPG no encontrado", 404
        
    except Exception as e:
        log_with_timestamp("ERROR", f"Error descargando archivo JPG: {str(e)}")
        return f"Error descargando archivo JPG: {str(e)}", 500

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

@app.route('/estado_sistema')
def estado_sistema():
    """Información del estado actual del sistema"""
    try:
        # Verificar archivos PDF
        pdf_protecta_existe = os.path.exists(processor.archivo_protecta)
        pdf_positiva_existe = os.path.exists(processor.archivo_positiva)
        
        # Verificar backups
        backup_protecta_existe = os.path.exists(f"{processor.archivo_protecta}.backup")
        backup_positiva_existe = os.path.exists(f"{processor.archivo_positiva}.backup")
        
        # Listar imágenes disponibles
        imagenes = processor.listar_imagenes_disponibles()
        numeros_disponibles = list(set([num for img in imagenes for num in img['numeros']]))
        
        # Archivos de resultado
        archivos_resultado = len([f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                                if f.startswith('resultado_')])
        
        return jsonify({
            'success': True,
            'archivos_pdf': {
                'protecta_existe': pdf_protecta_existe,
                'positiva_existe': pdf_positiva_existe,
                'backup_protecta_existe': backup_protecta_existe,
                'backup_positiva_existe': backup_positiva_existe
            },
            'imagenes_sistema': {
                'total_imagenes': len(imagenes),
                'numeros_disponibles': numeros_disponibles,
                'imagenes_detalle': imagenes
            },
            'archivos_resultado': archivos_resultado
            # Removido: 'configuracion': processor.configuracion  # Esta línea causaba el error 500
        })
        
    except Exception as e:
        log_with_timestamp("ERROR", f"Error obteniendo estado del sistema: {str(e)}")
        return jsonify({'error': f'Error obteniendo estado del sistema: {str(e)}'}), 500

@app.route('/test')
def test_endpoint():
    """Endpoint de prueba simple"""
    log_with_timestamp("INFO", "Endpoint de prueba llamado")
    return jsonify({
        'success': True,
        'message': 'Servidor funcionando correctamente',
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/test_post', methods=['POST'])
def test_post():
    """Endpoint de prueba para POST"""
    log_with_timestamp("INFO", "Endpoint POST de prueba llamado")
    log_with_timestamp("DEBUG", f"Request method: {request.method}")
    log_with_timestamp("DEBUG", f"Request content type: {request.content_type}")
    log_with_timestamp("DEBUG", f"Request form keys: {list(request.form.keys())}")
    log_with_timestamp("DEBUG", f"Request files keys: {list(request.files.keys())}")
    
    return jsonify({
        'success': True,
        'message': 'POST funcionando correctamente',
        'form_data': dict(request.form),
        'files': list(request.files.keys()),
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


def obtener_ip_local():
    """Obtiene la IP local de la maquina"""
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
    print(f"")
    print(f"[INFO] El servidor está configurado para ejecutarse en un host")
    print(f"   • Para acceso local: usa localhost o 127.0.0.1")
    print(f"   • Para acceso desde la red: usa la IP local mostrada")
    print("="*60)
    print("\n")

if __name__ == '__main__':
    # Mostrar informacion de acceso
    mostrar_informacion_acceso()
    
    # Configurar logging más detallado
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Iniciar servidor Flask para debug
    try:
        log_with_timestamp("INFO", "Iniciando servidor Flask en puerto 5000")
        print("=" * 60)
        print("SERVIDOR FLASK INICIADO EN MODO DEBUG")
        print("=" * 60)
        print("Logs detallados habilitados")
        print("Presiona Ctrl+C para detener el servidor")
        print("=" * 60)
        
        # Para debug, usar debug=True para ver errores detallados
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        log_with_timestamp("INFO", "Servidor detenido por el usuario")
    except Exception as e:
        log_with_timestamp("ERROR", f"Error iniciando servidor: {e}")
        print(f"Error detallado: {e}")
        import traceback
        traceback.print_exc()
        