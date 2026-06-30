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
    """Logging detallado para producción con formato ASCII"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Símbolos ASCII para diferentes niveles
    symbols = {
        'INFO': '[i]',
        'OK': '[+]',
        'WARNING': '[!]',
        'ERROR': '[x]',
        'DEBUG': '[?]',
        'STEP': '[>]'
    }
    
    symbol = symbols.get(level, '[?]')
    print(f"[{timestamp}] {symbol} {message}")

@app.route('/')
def index():
    """Página principal con el formulario"""
    return render_template('index.html')

@app.route('/procesar_soat', methods=['POST'])
def procesar_soat():
    """Procesa el SOAT con el monto ingresado"""
    try:
        log_with_timestamp("STEP", "=== INICIANDO PROCESAMIENTO SOAT CON MONTO ===")
        
        # Recibir datos del formulario
        archivo_pdf = request.files.get('pdf_file')
        monto = request.form.get('monto', '').strip()
        tipo_soat = request.form.get('tipo_soat')
        identificador = request.form.get('identificador', '').strip()
        
        log_with_timestamp("INFO", f"Datos recibidos - Tipo: {tipo_soat}, Monto: {monto}, ID: {identificador}")
        
        # Guardar identificador globalmente para las descargas
        # ultimo_identificador = identificador # Eliminado
        
        # Parámetros opcionales
        aplicar_mejoras = request.form.get('aplicar_mejoras', 'true').lower() == 'true'
        factor_brillo = float(request.form.get('factor_brillo', '1.15'))
        dpi_conversion = int(request.form.get('dpi', '300'))
        generar_pdf = request.form.get('generar_pdf', 'true').lower() == 'true'
        
        log_with_timestamp("INFO", f"Parametros - Mejoras: {aplicar_mejoras}, Brillo: {factor_brillo}, DPI: {dpi_conversion}, PDF: {generar_pdf}")
        
        # Validaciones básicas
        log_with_timestamp("STEP", "Validando datos de entrada...")
        
        if not archivo_pdf:
            log_with_timestamp("ERROR", "No se subio archivo PDF")
            return jsonify({'error': 'No se subió ningún archivo PDF'}), 400
            
        if not monto:
            log_with_timestamp("ERROR", "No se ingreso monto")
            return jsonify({'error': 'Debe ingresar un monto'}), 400
            
        if not tipo_soat or tipo_soat not in ['protecta', 'positiva', 'positiva_nueva']:
            log_with_timestamp("ERROR", f"Tipo de SOAT invalido: {tipo_soat}")
            return jsonify({'error': 'Debe seleccionar el tipo de SOAT (Protecta, Positiva o Positiva Nueva)'}), 400
        
        # Validar que el monto sea un número válido
        if not processor.validar_numero(monto):
            log_with_timestamp("ERROR", f"Monto invalido: {monto}")
            return jsonify({'error': 'El monto ingresado no es válido. Use solo números y decimales (ej: 170.00)'}), 400
        
        log_with_timestamp("OK", "Validaciones completadas exitosamente")
        
        # Validar parámetros de mejora
        if factor_brillo < 0.5 or factor_brillo > 2.0:
            factor_brillo = 1.15
            
        if dpi_conversion < 150 or dpi_conversion > 600:
            dpi_conversion = 300
        
        # Guardar archivo PDF temporalmente
        log_with_timestamp("STEP", f"Guardando archivo PDF temporalmente...")
        pdf_filename = secure_filename(archivo_pdf.filename)
        pdf_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{pdf_filename}")
        
        log_with_timestamp("INFO", f"Archivo original: {archivo_pdf.filename}")
        log_with_timestamp("INFO", f"Ruta temporal: {pdf_temp_path}")
        
        try:
            archivo_pdf.save(pdf_temp_path)
            log_with_timestamp("OK", "Archivo PDF guardado temporalmente")
        except Exception as e:
            log_with_timestamp("ERROR", f"Error guardando archivo PDF: {str(e)}")
            return jsonify({'error': f'Error guardando archivo PDF: {str(e)}'}), 500
        
        # Verificar que el archivo se guardó correctamente
        if not os.path.exists(pdf_temp_path):
            log_with_timestamp("ERROR", "Archivo PDF no se guardo correctamente")
            return jsonify({'error': 'Error guardando archivo PDF'}), 500

        # Generar nombre de archivo usando SOLO el identificador
        log_with_timestamp("STEP", "Generando nombre de archivo resultado...")
        if identificador:
            # Limpiar identificador para usar como nombre de archivo
            identificador_limpio = "".join(c for c in identificador if c.isalnum() or c in "._-")
            resultado_filename = f"{identificador_limpio}.jpg"
        else:
            # Si no hay identificador, usar formato original
            resultado_filename = f"resultado_{tipo_soat}_{monto}_{pdf_filename.replace('.pdf', '.jpg')}"
        
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], resultado_filename)
        log_with_timestamp("INFO", f"Archivo resultado: {resultado_filename}")
        
        # Procesar SOAT con dígitos
        log_with_timestamp("STEP", "Iniciando procesamiento de SOAT con digitos...")
        # Parámetro para detección automática
        detectar_identificador_auto = request.form.get('detectar_identificador_auto', 'true').lower() == 'true'
        
        resultado = processor.procesar_soat_con_digitos(
            tipo_soat=tipo_soat,
            numero=monto,
            pdf_path=pdf_temp_path,
            archivo_salida=resultado_path,
            aplicar_mejoras=aplicar_mejoras,
            factor_brillo=factor_brillo,
            dpi_conversion=dpi_conversion,
            redimensionar_final=True,
            ancho_final=1694,
            alto_final=3300,
            generar_pdf=True,
            detectar_identificador_auto=detectar_identificador_auto
        )
        
        # Limpiar archivo temporal
        log_with_timestamp("STEP", "Limpiando archivo temporal...")
        try:
            os.remove(pdf_temp_path)
            log_with_timestamp("OK", "Archivo temporal eliminado")
        except:
            log_with_timestamp("WARNING", "No se pudo eliminar archivo temporal")
        
        if resultado['success']:
            log_with_timestamp("OK", "Procesamiento completado exitosamente")
            
            # Obtener la imagen resultado del procesamiento
            # (procesar_soat_con_digitos ya guardó el JPG y el PDF en disco)
            imagen_resultado = resultado['imagen_resultado']

            # Convertir la imagen a base64 para mostrar en el frontend
            log_with_timestamp("STEP", "Convirtiendo imagen a base64 para frontend...")
            _, buffer = cv2.imencode('.jpg', imagen_resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            log_with_timestamp("OK", "Imagen convertida a base64")
            
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
            
            log_with_timestamp("OK", "=== PROCESAMIENTO SOAT CON MONTO COMPLETADO EXITOSAMENTE ===")
            
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
                'info_procesamiento': info_procesamiento,
                'identificador_detectado': resultado.get('identificador_detectado', ''),
                'identificador_usado': resultado.get('identificador_usado', 'manual')
            })
        else:
            log_with_timestamp("ERROR", f"Error en procesamiento: {resultado['error']}")
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
        log_with_timestamp("STEP", "=== INICIANDO PROCESAMIENTO SOAT SIN MONTO ===")
        
        # Recibir datos del formulario
        archivo_pdf = request.files.get('pdf_file')
        tipo_soat = request.form.get('tipo_soat')
        identificador = request.form.get('identificador', '').strip()
        detectar_identificador_auto = request.form.get('detectar_identificador_auto', 'false').lower() == 'true'
        
        log_with_timestamp("INFO", f"Datos recibidos - Tipo: {tipo_soat}, ID: {identificador}, Auto: {detectar_identificador_auto}")
        
        # Parámetros opcionales
        aplicar_mejoras = request.form.get('aplicar_mejoras', 'true').lower() == 'true'
        factor_brillo = float(request.form.get('factor_brillo', '1.3'))
        dpi_conversion = int(request.form.get('dpi', '300'))
        generar_pdf = request.form.get('generar_pdf', 'true').lower() == 'true'
        
        log_with_timestamp("INFO", f"Parametros - Mejoras: {aplicar_mejoras}, Brillo: {factor_brillo}, DPI: {dpi_conversion}, PDF: {generar_pdf}")
        
        # Validaciones básicas
        log_with_timestamp("STEP", "Validando datos de entrada...")
        
        if not archivo_pdf:
            log_with_timestamp("ERROR", "No se subio archivo PDF")
            return jsonify({'error': 'No se subió ningún archivo PDF'}), 400
            
        if not tipo_soat or tipo_soat not in ['protecta', 'positiva', 'positiva_nueva']:
            log_with_timestamp("ERROR", f"Tipo de SOAT invalido: {tipo_soat}")
            return jsonify({'error': 'Debe seleccionar el tipo de SOAT (Protecta, Positiva o Positiva Nueva)'}), 400
        
        log_with_timestamp("OK", "Validaciones completadas exitosamente")
        
        # Validar parámetros de mejora
        if factor_brillo < 0.5 or factor_brillo > 2.0:
            factor_brillo = 1.3
            
        if dpi_conversion < 150 or dpi_conversion > 600:
            dpi_conversion = 300
        
        # Guardar archivo PDF temporalmente
        pdf_filename = secure_filename(archivo_pdf.filename)
        pdf_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{pdf_filename}")
        archivo_pdf.save(pdf_temp_path)

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
            pdf_path=pdf_temp_path,
            archivo_salida=resultado_path,
            aplicar_mejoras=aplicar_mejoras,
            factor_brillo=factor_brillo,
            dpi_conversion=dpi_conversion,
            redimensionar_final=True,
            ancho_final=1694,
            alto_final=3300,
            generar_pdf=True,
            detectar_identificador_auto=detectar_identificador_auto
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
                'info_procesamiento': info_procesamiento,
                'identificador_detectado': resultado.get('identificador_detectado', ''),
                'identificador_usado': resultado.get('identificador_usado', 'manual')
            })
        else:
            return jsonify({'error': resultado['error']}), 400
        
    except ValueError as ve:
        return jsonify({'error': f'Error en los parámetros: {str(ve)}'}), 400
    except Exception as e:
        log_with_timestamp("ERROR", f"Error del servidor: {str(e)}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

def _descargar_resultado(nombre_solicitado: str, extension: str):
    """Sirve el archivo resultado pedido (por nombre) o el más reciente como fallback.

    Recibir el nombre concreto evita que, con varias peticiones simultáneas,
    un usuario descargue el SOAT generado por otro.
    """
    carpeta = app.config['UPLOAD_FOLDER']

    # 1. Si el cliente indicó el archivo, servir exactamente ese (saneado).
    if nombre_solicitado:
        base = os.path.splitext(secure_filename(nombre_solicitado))[0] + extension
        ruta = os.path.join(carpeta, base)
        if os.path.isfile(ruta):
            return send_file(ruta, as_attachment=True, download_name=base)

    # 2. Fallback: archivo más reciente con esa extensión (excluyendo temporales).
    candidatos = [f for f in os.listdir(carpeta)
                  if f.endswith(extension) and not f.startswith('temp_')]
    if not candidatos:
        return f"No hay archivos {extension} procesados disponibles para descargar", 404

    reciente = max(candidatos, key=lambda x: os.path.getctime(os.path.join(carpeta, x)))
    return send_file(os.path.join(carpeta, reciente), as_attachment=True, download_name=reciente)

@app.route('/descargar_jpg')
def descargar_jpg():
    """Descargar el SOAT procesado en formato JPG"""
    try:
        return _descargar_resultado(request.args.get('archivo'), '.jpg')
    except Exception as e:
        log_with_timestamp("ERROR", f"Error descargando archivo JPG: {str(e)}")
        return f"Error descargando archivo JPG: {str(e)}", 500

@app.route('/descargar_pdf')
def descargar_pdf():
    """Descargar el SOAT procesado en formato PDF"""
    try:
        return _descargar_resultado(request.args.get('archivo'), '.pdf')
    except Exception as e:
        log_with_timestamp("ERROR", f"Error descargando archivo PDF: {str(e)}")
        return f"Error descargando archivo PDF: {str(e)}", 500

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
    puerto = int(os.environ.get("PORT", 5000))

    print("\n" + "="*60)
    print("EDITOR SOAT - SERVIDOR FLASK INICIADO")
    print("="*60)
    print(f"[LOCAL] Acceso Local:")
    print(f"   -> http://localhost:{puerto}")
    print(f"   -> http://127.0.0.1:{puerto}")
    print(f"")
    print(f"[RED] Acceso Red Local (misma red):")
    print(f"   -> http://{ip_local}:{puerto}")
    print("="*60)
    print("\n")

if __name__ == '__main__':
    # Host y puerto configurables por entorno (HOST / PORT).
    host = os.environ.get("HOST", "0.0.0.0")
    puerto = int(os.environ.get("PORT", 5000))

    # Mostrar información de acceso
    mostrar_informacion_acceso()

    # Servidor de desarrollo. En producción usar Gunicorn:
    #   gunicorn -w 2 -b 0.0.0.0:5000 recepcion_imagen:app
    try:
        print(f"Iniciando servidor Flask en {host}:{puerto}...")
        app.run(debug=False, host=host, port=puerto)
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario")
    except Exception as e:
        print(f"Error iniciando servidor: {e}")
        