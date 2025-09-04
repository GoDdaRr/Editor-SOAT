# app_flask.py
from flask import Flask, render_template, request, send_file, jsonify
import os
from werkzeug.utils import secure_filename
import base64
import cv2

# Importar nuestro procesador desde main.py
from main import SOATProcessor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Instancia del procesador SOAT
processor = SOATProcessor()

@app.route('/')
def index():
    """Página principal con el formulario simplificado"""
    return render_template('index.html')

@app.route('/procesar_soat', methods=['POST'])
def procesar_soat():
    """Procesa el SOAT con el monto ingresado usando la nueva funcionalidad de dígitos con posiciones fijas"""
    try:
        # Recibir datos del formulario
        archivo_pdf = request.files.get('pdf_file')
        monto = request.form.get('monto', '').strip()
        tipo_soat = request.form.get('tipo_soat')
        
        # Parámetros opcionales para mejoras
        aplicar_mejoras = request.form.get('aplicar_mejoras', 'true').lower() == 'true'
        factor_brillo = float(request.form.get('factor_brillo', '1.15'))
        dpi_conversion = int(request.form.get('dpi', '300'))
        
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
            factor_brillo = 1.15  # Valor por defecto
            
        if dpi_conversion < 150 or dpi_conversion > 600:
            dpi_conversion = 300  # Valor por defecto
        
        # Guardar archivo PDF temporalmente
        pdf_filename = secure_filename(archivo_pdf.filename)
        pdf_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{pdf_filename}")
        archivo_pdf.save(pdf_temp_path)
        
        # Actualizar archivo PDF correspondiente
        if not processor.actualizar_archivo_pdf(tipo_soat, pdf_temp_path):
            return jsonify({'error': f'No se pudo actualizar el archivo {tipo_soat}. Verifique que el PDF sea válido.'}), 500
        
        # Procesar SOAT con la nueva funcionalidad de dígitos
        resultado_filename = f"resultado_{tipo_soat}_{monto}_{pdf_filename.replace('.pdf', '.jpg')}"
        resultado_path = os.path.join(app.config['UPLOAD_FOLDER'], resultado_filename)
        
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
            alto_final=3300
        )
        
        # Limpiar archivo temporal
        try:
            os.remove(pdf_temp_path)
        except:
            pass  # No importa si no se puede eliminar
        
        if resultado['success']:
            # Convertir imagen resultado a base64 para mostrar en el frontend
            imagen_resultado = resultado['imagen_resultado']
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
                'posiciones_utilizadas': resultado.get('posiciones_utilizadas', {})
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
                'info_procesamiento': info_procesamiento
            })
        else:
            return jsonify({'error': resultado['error']}), 400
        
    except ValueError as ve:
        return jsonify({'error': f'Error en los parámetros: {str(ve)}'}), 400
    except Exception as e:
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
        return f"Error descargando archivo: {str(e)}", 500

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
            'archivos_resultado': archivos_resultado,
            'configuracion': processor.configuracion
        })
        
    except Exception as e:
        return jsonify({'error': f'Error obteniendo estado del sistema: {str(e)}'}), 500


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

def configurar_ngrok():
    """Configura ngrok para acceso remoto"""
    try:
        import subprocess
        import threading
        import time
        
        # Intentar ejecutar ngrok directamente
        def ejecutar_ngrok():
            try:
                subprocess.run(['ngrok', 'http', '5000'], check=True)
            except:
                pass
        
        # Ejecutar ngrok en segundo plano
        ngrok_thread = threading.Thread(target=ejecutar_ngrok, daemon=True)
        ngrok_thread.start()
        
        # Esperar un poco para que ngrok se configure
        time.sleep(3)
        
        print("[INFO] Ngrok iniciado manualmente.")
        print("[INFO] Visita http://localhost:4040 para ver la URL publica")
        
        return "http://localhost:4040"
        
    except Exception as e:
        print(f"[ERROR] Error configurando ngrok: {e}")
        print("[INFO] Ejecuta manualmente: ngrok http 5000")
        return None

def mostrar_informacion_acceso():
    """Muestra todas las formas de acceso al servidor"""
    ip_local = obtener_ip_local()
    url_remota = configurar_ngrok()
    
    print("\n" + "="*60)
    print("EDITOR SOAT - SERVIDOR FLASK INICIADO")
    print("="*60)
    print(f"[LOCAL] Acceso Local:")
    print(f"   -> http://localhost:5000")
    print(f"   -> http://127.0.0.1:5000")
    print(f"")
    print(f"[RED] Acceso Red Local (misma WiFi):")
    print(f"   -> http://{ip_local}:5000")
    print(f"")
    
    if url_remota:
        print(f"[REMOTO] Acceso desde cualquier red:")
        print(f"   -> {url_remota}")
        print(f"   [OK] Compartir esta URL para acceso desde cualquier lugar")
    else:
        print(f"[WARNING] Acceso Remoto no disponible")
        print(f"   -> Instala pyngrok: pip install pyngrok")
    
    print(f"")
    print(f"[INFO] Consejos:")
    print(f"   • Para dispositivos en la misma red: usa la URL de Red Local")
    print(f"   • Para acceso desde internet: usa la URL Remota")
    print(f"   • La URL remota cambia cada vez que reinicias el servidor")
    print("="*60)
    print("\n")

if __name__ == '__main__':
    # Mostrar informacion de acceso
    mostrar_informacion_acceso()
    
    # Iniciar servidor Flask
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n[STOP] Servidor detenido por el usuario")
    except Exception as e:
        print(f"\n[ERROR] Error iniciando servidor: {e}")