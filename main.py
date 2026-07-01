import cv2
from pdf2image import convert_from_path
import numpy as np
import os
from typing import Optional, List
from PIL import Image
import datetime
import pytesseract
import re

class SOATProcessor:
    def __init__(self):
        # Poppler (binario para convertir PDF -> imagen).
        # Se puede forzar la ruta con la variable de entorno POPPLER_PATH.
        # Si no se define, se usa el binario disponible en el PATH del sistema
        # (caso normal en Linux con poppler-utils instalado).
        self.poppler_path = os.environ.get("POPPLER_PATH") or None
        if not self.poppler_path:
            # Fallback para desarrollo en Windows con Poppler portátil local.
            local_win = os.path.abspath("poppler/poppler-24.02.0/Library/bin")
            if os.path.exists(local_win):
                self.poppler_path = local_win

        # Extensiones de imagen soportadas
        self.extensiones_imagen = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
    
    def log_with_timestamp(self, level: str, message: str):
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
    
    def buscar_imagen_por_numero(self, numero: str, tipo_soat: str = "protecta") -> Optional[str]:
        """Busca una imagen en el sistema que contenga el numero en su nombre"""
        if tipo_soat == "positiva_nueva":
            # Usa imágenes propias si existen; si no, reutiliza las de Positiva.
            directorios_busqueda = ["assets/assets-positiva-nueva", "assets/assets-positiva", "assets", ".", "imagenes", "recursos"]
        elif tipo_soat == "positiva":
            directorios_busqueda = ["assets/assets-positiva", "assets", ".", "imagenes", "recursos"]
        else:
            directorios_busqueda = ["assets/assets-protecta", "assets/antiguos", "assets", ".", "imagenes", "recursos"]
        
        for directorio in directorios_busqueda:
            if not os.path.exists(directorio):
                continue
                
            try:
                archivos = os.listdir(directorio)
                
                for archivo in archivos:
                    ruta_completa = os.path.join(directorio, archivo)
                    
                    if not os.path.isfile(ruta_completa):
                        continue
                        
                    nombre_lower = archivo.lower()
                    es_imagen = any(nombre_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'])
                    
                    if es_imagen and (numero in archivo or f"numero-{numero}-nuevo" in archivo):
                        return ruta_completa
                        
            except Exception as e:
                self.log_with_timestamp("WARNING", f"Error accediendo a {directorio}: {e}")
                continue
        
        return None
    
    def validar_numero(self, numero_str: str) -> bool:
        """Valida que el string sea un numero valido"""
        try:
            caracteres_validos = set('0123456789.,')
            if not all(c in caracteres_validos for c in numero_str):
                return False
            float(numero_str.replace(',', '.'))
            return True
        except:
            return False
    
    def descomponer_numero_en_digitos(self, numero: str) -> List[str]:
        """Descompone un número en sus dígitos individuales"""
        try:
            numero_limpio = numero.replace('.', '').replace(',', '')
            
            if not numero_limpio.isdigit():
                return []
            
            if len(numero_limpio) > 3:
                numero_limpio = numero_limpio[:3]
            
            return list(numero_limpio)
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error descomponiendo número {numero}: {e}")
            return []

    def buscar_imagenes_por_digitos(self, digitos: List[str], tipo_soat: str) -> tuple:
        """Busca imágenes para cada dígito individual"""
        imagenes_encontradas = []
        digitos_no_encontrados = []
        
        for i, digito in enumerate(digitos):
            ruta_imagen = self.buscar_imagen_por_numero(digito, tipo_soat)
            
            if ruta_imagen:
                imagenes_encontradas.append({
                    'digito': digito,
                    'posicion': i,
                    'ruta': ruta_imagen,
                    'encontrada': True
                })
            else:
                digitos_no_encontrados.append(digito)
                imagenes_encontradas.append({
                    'digito': digito,
                    'posicion': i,
                    'ruta': None,
                    'encontrada': False
                })
        
        return imagenes_encontradas, digitos_no_encontrados

    def convertir_imagen_a_pdf(self, imagen_path: str, pdf_path: str) -> bool:
        """Convierte una imagen a formato PDF"""
        try:
            imagen = Image.open(imagen_path)
            
            if imagen.mode != 'RGB':
                imagen = imagen.convert('RGB')
            
            imagen.save(pdf_path, 'PDF', resolution=300.0, quality=95)
            return True
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error convirtiendo imagen a PDF: {e}")
            return False

    def procesar_soat_con_digitos(self,
                                tipo_soat: str,
                                numero: str,
                                pdf_path: str,
                                archivo_salida: str = "resultado.jpg",
                                aplicar_mejoras: bool = True,
                                factor_brillo: float = 1.1,
                                dpi_conversion: int = 300,
                                redimensionar_final: bool = False,
                                ancho_final: int = 1694,
                                alto_final: int = 3300,
                                generar_pdf: bool = True,
                                detectar_identificador_auto: bool = False) -> dict:
        """Procesa SOAT descomponiendo el número en dígitos individuales"""
        try:
            self.log_with_timestamp("STEP", f"Iniciando procesamiento SOAT {tipo_soat.upper()} con monto: {numero}")
            
            # Validar y descomponer número
            self.log_with_timestamp("STEP", f"Validando numero: {numero}")
            if not self.validar_numero(numero):
                self.log_with_timestamp("ERROR", f"Numero invalido: {numero}")
                return {'success': False, 'error': 'El número ingresado no es válido.'}
            
            self.log_with_timestamp("OK", f"Numero validado correctamente")
            
            digitos = self.descomponer_numero_en_digitos(numero)
            if not digitos:
                self.log_with_timestamp("ERROR", f"No se pudo descomponer el numero: {numero}")
                return {'success': False, 'error': 'No se pudo descomponer el número en dígitos.'}
            
            self.log_with_timestamp("OK", f"Numero descompuesto en digitos: {digitos}")
            
            # Buscar imágenes para cada dígito
            self.log_with_timestamp("STEP", f"Buscando imagenes para {len(digitos)} digitos...")
            imagenes_info, digitos_no_encontrados = self.buscar_imagenes_por_digitos(digitos, tipo_soat)
            
            if digitos_no_encontrados:
                self.log_with_timestamp("ERROR", f"Digitos no encontrados: {digitos_no_encontrados}")
                return {
                    'success': False, 
                    'error': f'No se encontraron imágenes para los dígitos: {", ".join(digitos_no_encontrados)}'
                }
            
            self.log_with_timestamp("OK", f"Todas las imagenes de digitos encontradas")
            
            # Convertir PDF a imagen
            self.log_with_timestamp("STEP", f"Convirtiendo PDF {tipo_soat} a imagen (DPI: {dpi_conversion})")
            fondo = self.pdf_to_image_mejorada(pdf_path, dpi_conversion, aplicar_mejoras, factor_brillo)
            if fondo is None:
                self.log_with_timestamp("ERROR", f"Error convirtiendo PDF de {tipo_soat}")
                return {'success': False, 'error': f'No se pudo procesar el PDF de {tipo_soat}'}
            
            self.log_with_timestamp("OK", f"PDF convertido exitosamente, dimensiones: {fondo.shape[1]}x{fondo.shape[0]}")
            
            # Redimensionar fondo si está habilitado
            dimensiones_originales = f'{fondo.shape[1]}x{fondo.shape[0]}'
            
            if redimensionar_final:
                self.log_with_timestamp("STEP", f"Redimensionando fondo a {ancho_final}x{alto_final}")
                fondo = self.redimensionar_resultado_final(fondo, ancho_final, alto_final)
                self.log_with_timestamp("OK", f"Fondo redimensionado correctamente")
                
                if aplicar_mejoras:
                    self.log_with_timestamp("STEP", "Aplicando saturacion a region especifica...")
                    fondo = self.saturar_region_rectangulo(fondo, 35, 2525, 1661, 2780, 1.6)
                    self.log_with_timestamp("OK", "Saturacion de region aplicada")
            
            # Configuración de posiciones fijas para cada dígito
            posiciones_digitos = {
                'protecta': {
                    0: {'x': 936, 'y': 1771},
                    1: {'x': 966, 'y': 1771},
                    2: {'x': 995, 'y': 1771}
                },
                'positiva': {
                    0: {'x': 918, 'y': 2194},
                    1: {'x': 954, 'y': 2194},
                    2: {'x': 991, 'y': 2194}
                },
                # Positiva (Nueva): dígitos reducidos (assets-positiva-nueva, ~26x45)
                # para igualar la fuente del nuevo layout. Separación ~27 px.
                'positiva_nueva': {
                    0: {'x': 938, 'y': 1866},
                    1: {'x': 965, 'y': 1866},
                    2: {'x': 992, 'y': 1866}
                }
            }
            
            # Procesar cada dígito en su posición fija
            self.log_with_timestamp("STEP", f"Pegando {len(imagenes_info)} digitos en posiciones fijas...")
            resultado = fondo.copy()
            imagenes_pegadas = []
            
            for img_info in imagenes_info:
                if not img_info['encontrada']:
                    continue
                
                self.log_with_timestamp("STEP", f"Cargando imagen para digito '{img_info['digito']}' desde: {img_info['ruta']}")
                imagen_digito = cv2.imread(img_info['ruta'])
                if imagen_digito is None:
                    self.log_with_timestamp("ERROR", f"No se pudo cargar imagen para digito '{img_info['digito']}'")
                    continue
                
                posicion_digito = img_info['posicion']
                if posicion_digito not in posiciones_digitos[tipo_soat]:
                    self.log_with_timestamp("ERROR", f"Posicion {posicion_digito} no definida para {tipo_soat}")
                    continue
                
                x_posicion = posiciones_digitos[tipo_soat][posicion_digito]['x']
                y_posicion = posiciones_digitos[tipo_soat][posicion_digito]['y']
                
                h_digito, w_digito = imagen_digito.shape[:2]
                h_fondo, w_fondo = resultado.shape[:2]
                
                self.log_with_timestamp("INFO", f"Pegando digito '{img_info['digito']}' ({w_digito}x{h_digito}) en posicion ({x_posicion},{y_posicion})")
                
                if x_posicion + w_digito > w_fondo or y_posicion + h_digito > h_fondo:
                    self.log_with_timestamp("ERROR", f"Digito '{img_info['digito']}' se sale de los limites del fondo")
                    continue
                
                resultado[y_posicion:y_posicion+h_digito, x_posicion:x_posicion+w_digito] = imagen_digito
                self.log_with_timestamp("OK", f"Digito '{img_info['digito']}' pegado exitosamente")
                
                imagenes_pegadas.append({
                    'digito': img_info['digito'],
                    'posicion': img_info['posicion'],
                    'coordenadas_fijas': f'({x_posicion},{y_posicion})',
                    'dimensiones': f'{w_digito}x{h_digito}'
                })
            
            self.log_with_timestamp("OK", f"Todos los digitos pegados correctamente")
            
            # Aplicar saturación general a toda la imagen como paso final
            self.log_with_timestamp("STEP", "Aplicando saturacion general a toda la imagen...")
            factor_saturacion_final = 1.8  # CONFIGURABLE INTERNAMENTE
            resultado = self.saturar_imagen_completa(resultado, factor_saturacion_final)
            self.log_with_timestamp("OK", "Saturacion general aplicada")
            
            # Detectar identificador automáticamente si se solicita
            identificador_detectado = ""
            identificador_usado = "manual"

            if detectar_identificador_auto:
                self.log_with_timestamp("STEP", "Iniciando detección automática de identificador...")
                identificador_detectado = self.detectar_identificador_automatico(resultado, tipo_soat)
                
                if identificador_detectado:
                    # Usar el identificador detectado para el nombre del archivo.
                    # El PDF se deriva de archivo_salida al generarse más abajo.
                    identificador_limpio = "".join(c for c in identificador_detectado if c.isalnum() or c in "._-")
                    archivo_salida = f"{identificador_limpio}.jpg"
                    identificador_usado = "automatico"
            
            # Guardar la imagen final
            self.log_with_timestamp("STEP", f"Guardando imagen final: {archivo_salida}")
            cv2.imwrite(archivo_salida, resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            self.log_with_timestamp("OK", f"Imagen guardada exitosamente")
            
            # Generar PDF si está habilitado
            archivo_pdf = None
            if generar_pdf:
                pdf_path = archivo_salida.replace('.jpg', '.pdf')
                self.log_with_timestamp("STEP", f"Generando PDF: {pdf_path}")
                if self.convertir_imagen_a_pdf(archivo_salida, pdf_path):
                    archivo_pdf = pdf_path
                    self.log_with_timestamp("OK", f"PDF generado exitosamente")
                else:
                    self.log_with_timestamp("WARNING", "No se pudo generar el PDF")
            
            self.log_with_timestamp("OK", f"Procesamiento SOAT {tipo_soat.upper()} completado exitosamente")
            self.log_with_timestamp("INFO", f"Resumen: {len(digitos)} digitos procesados, dimensiones finales: {resultado.shape[1]}x{resultado.shape[0]}")
            
            return {
                'success': True,
                'mensaje': f'SOAT {tipo_soat.upper()} procesado correctamente con número: {numero}',
                'tipo_soat': tipo_soat,
                'numero': numero,
                'digitos': digitos,
                'imagenes_pegadas': imagenes_pegadas,
                'total_digitos': len(digitos),
                'posiciones_utilizadas': posiciones_digitos[tipo_soat],
                'mejoras_aplicadas': aplicar_mejoras,
                'factor_brillo_usado': factor_brillo,
                'dpi_usado': dpi_conversion,
                'imagen_origen': 'descompuesto en dígitos con posiciones fijas',
                'dimensiones_originales': dimensiones_originales,
                'dimensiones_finales': f'{resultado.shape[1]}x{resultado.shape[0]}',
                'redimensionado': redimensionar_final,
                'archivo_salida': archivo_salida,
                'archivo_pdf': archivo_pdf,
                'imagen_resultado': resultado,
                'identificador_detectado': identificador_detectado,
                'identificador_usado': identificador_usado
            }
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error interno procesando dígitos: {str(e)}")
            return {'success': False, 'error': f'Error interno procesando dígitos: {str(e)}'}
    
    def _render_pdf_bgr(self, pdf_path: str, dpi: int) -> np.ndarray:
        """Renderiza la primera página del PDF a un array BGR de OpenCV.

        Usa Poppler (pdf2image) si está disponible. Si no lo está (p. ej. en
        desarrollo local sin Poppler), cae a PyMuPDF, que no requiere binarios
        del sistema. Ambos producen la misma geometría tras el redimensionado.
        """
        # 1. Poppler / pdf2image (opción por defecto en el servidor)
        try:
            pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=self.poppler_path)
            return cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.log_with_timestamp("WARNING", f"Poppler no disponible ({e}); usando PyMuPDF")

        # 2. PyMuPDF (fitz) como alternativa sin dependencias del sistema
        import fitz
        doc = fitz.open(pdf_path)
        try:
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            modo = cv2.COLOR_RGBA2BGR if pix.n == 4 else cv2.COLOR_RGB2BGR
            return cv2.cvtColor(img, modo)
        finally:
            doc.close()

    def pdf_to_image_mejorada(self, pdf_path: str, dpi: int = 300, aplicar_mejoras: bool = True,
                             factor_brillo: float = 1.2) -> Optional[np.ndarray]:
        """Convierte el PDF indicado a imagen con mejoras configurables"""
        try:
            self.log_with_timestamp("INFO", f"Archivo PDF: {pdf_path}")

            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"No se encuentra el archivo: {pdf_path}")

            self.log_with_timestamp("INFO", f"Poppler: {self.poppler_path or 'PATH del sistema'}")

            # Convertir PDF a imagen (poppler_path=None -> se busca en el PATH)
            self.log_with_timestamp("STEP", f"Ejecutando conversion PDF->imagen (DPI: {dpi})")
            imagen_cv = self._render_pdf_bgr(pdf_path, dpi)
            self.log_with_timestamp("OK", f"Conversion completada, dimensiones: {imagen_cv.shape}")
            
            # Aplicar mejoras si está habilitado
            if aplicar_mejoras:
                self.log_with_timestamp("STEP", f"Aplicando aumento de brillo (factor: {factor_brillo})")
                imagen_cv = self.aumentar_brillo(imagen_cv, factor_brillo=factor_brillo)
                self.log_with_timestamp("OK", "Brillo aplicado correctamente")
            
            return imagen_cv
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error convirtiendo PDF a imagen: {e}")
            return None

    def aumentar_brillo(self, imagen: np.ndarray, factor_brillo: float = 1.2) -> np.ndarray:
        """Aumenta el brillo de una imagen"""
        try:
            self.log_with_timestamp("STEP", f"Aplicando aumento de brillo (factor: {factor_brillo})")
            imagen_float = imagen.astype(np.float32)
            imagen_brillante = imagen_float * factor_brillo
            imagen_brillante = np.clip(imagen_brillante, 0, 255)
            resultado = imagen_brillante.astype(np.uint8)
            self.log_with_timestamp("OK", f"Brillo aumentado correctamente")
            return resultado
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error aumentando brillo: {e}")
            return imagen

    def redimensionar_resultado_final(self, imagen: np.ndarray, ancho_objetivo: int = 1694, alto_objetivo: int = 3300) -> np.ndarray:
        """Redimensiona la imagen final a un tamaño específico"""
        try:
            alto_actual, ancho_actual = imagen.shape[:2]
            self.log_with_timestamp("STEP", f"Redimensionando imagen de {ancho_actual}x{alto_actual} a {ancho_objetivo}x{alto_objetivo}")
            resultado = cv2.resize(imagen, (ancho_objetivo, alto_objetivo), interpolation=cv2.INTER_CUBIC)
            self.log_with_timestamp("OK", f"Imagen redimensionada correctamente")
            return resultado
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error redimensionando imagen: {e}")
            return imagen

    def saturar_region_rectangulo(self, imagen: np.ndarray, x1: int, y1: int, x2: int, y2: int, 
                             factor_saturacion: float = 1.6) -> np.ndarray:
        """Satura una región rectangular específica"""
        try:
            self.log_with_timestamp("STEP", f"Saturando region rectangular ({x1},{y1}) a ({x2},{y2}) con factor {factor_saturacion}")
            resultado = imagen.copy()
            h_img, w_img = imagen.shape[:2]
            
            x_inicio = min(x1, x2)
            y_inicio = min(y1, y2)
            x_fin = max(x1, x2)
            y_fin = max(y1, y2)
            
            if x_inicio < 0 or y_inicio < 0 or x_fin >= w_img or y_fin >= h_img:
                self.log_with_timestamp("ERROR", f"Region fuera de limites de la imagen")
                return imagen
            
            region = imagen[y_inicio:y_fin+1, x_inicio:x_fin+1].copy()
            region_hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(region_hsv)
            
            s_float = s.astype(np.float32)
            s_saturada = s_float * factor_saturacion
            s_saturada = np.clip(s_saturada, 0, 255).astype(np.uint8)
            
            region_hsv_saturada = cv2.merge([h, s_saturada, v])
            region_saturada = cv2.cvtColor(region_hsv_saturada, cv2.COLOR_HSV2BGR)
            
            resultado[y_inicio:y_fin+1, x_inicio:x_fin+1] = region_saturada
            
            ancho = x_fin - x_inicio + 1
            alto = y_fin - y_inicio + 1
            self.log_with_timestamp("OK", f"Region saturada: {ancho}x{alto} pixeles")
            
            return resultado
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error saturando región: {e}")
            return imagen

    def saturar_imagen_completa(self, imagen: np.ndarray, factor_saturacion: float = 1.9) -> np.ndarray:
        """
        Aplica saturación a toda la imagen completa - PASO FINAL DE MEJORA
        
        Esta función se aplica al final del procesamiento, antes de la descarga,
        para mejorar la saturación de colores de toda la imagen resultado.
        
        Args:
            imagen: Imagen en formato OpenCV (numpy array)
            factor_saturacion: Factor de saturación (1.0 = sin cambio, >1.0 = más saturado)
            
        Returns:
            np.ndarray: Imagen con saturación aplicada a toda la imagen
        """
        try:
            # Convertir a HSV para manipular saturación
            imagen_hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV)
            
            # Separar canales H, S, V
            h, s, v = cv2.split(imagen_hsv)
            
            # Aumentar saturación (canal S) en toda la imagen
            s_float = s.astype(np.float32)
            s_saturada = s_float * factor_saturacion
            
            # Asegurar que esté en rango [0, 255]
            s_saturada = np.clip(s_saturada, 0, 255).astype(np.uint8)
            
            # Recombinar canales
            imagen_hsv_saturada = cv2.merge([h, s_saturada, v])
            
            # Convertir de vuelta a BGR
            imagen_saturada = cv2.cvtColor(imagen_hsv_saturada, cv2.COLOR_HSV2BGR)
            
            self.log_with_timestamp("OK", f"Saturación general aplicada con factor: {factor_saturacion}")
            return imagen_saturada
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error aplicando saturación general: {e}")
            return imagen

    def procesar_soat_sin_monto(self,
                               tipo_soat: str,
                               pdf_path: str,
                               archivo_salida: str = "resultado_sin_monto.jpg",
                               aplicar_mejoras: bool = True,
                               factor_brillo: float = 1.2,
                               dpi_conversion: int = 300,
                               redimensionar_final: bool = False,
                               ancho_final: int = 1694,
                               alto_final: int = 3300,
                               generar_pdf: bool = True,
                               detectar_identificador_auto: bool = False) -> dict:
        """Procesa SOAT sin monto - solo pega la imagen sin-monto.jpg"""
        try:
            # Buscar imagen sin monto
            imagen_sin_monto = self.buscar_imagen_por_numero("sin-monto", tipo_soat)
            if not imagen_sin_monto:
                return {'success': False, 'error': 'No se encontró la imagen sin-monto.jpg'}
            
            # Convertir PDF a imagen
            fondo = self.pdf_to_image_mejorada(pdf_path, dpi_conversion, aplicar_mejoras, factor_brillo)
            if fondo is None:
                return {'success': False, 'error': f'No se pudo procesar el PDF de {tipo_soat}'}
            
            # Detectar identificador automáticamente si está habilitado
            identificador_detectado = ""
            if detectar_identificador_auto:
                self.log_with_timestamp("STEP", "Detectando identificador automáticamente...")
                identificador_detectado = self.detectar_identificador_automatico(fondo, tipo_soat)
                if identificador_detectado and identificador_detectado != "NO_DETECTADO":
                    self.log_with_timestamp("OK", f"Identificador detectado: {identificador_detectado}")
                    # Actualizar el nombre del archivo con el identificador detectado
                    if identificador_detectado:
                        identificador_limpio = "".join(c for c in identificador_detectado if c.isalnum() or c in "._-")
                        archivo_salida = archivo_salida.replace("resultado_sin_monto", f"resultado_{tipo_soat}_{identificador_limpio}")
                else:
                    self.log_with_timestamp("WARNING", "No se pudo detectar identificador automáticamente")
            
            # Redimensionar fondo si está habilitado
            if redimensionar_final:
                fondo = self.redimensionar_resultado_final(fondo, ancho_final, alto_final)
                
                if aplicar_mejoras:
                    fondo = self.saturar_region_rectangulo(fondo, 35, 2525, 1661, 2780, 1.6)
            
            # Cargar imagen sin monto
            imagen_digito = cv2.imread(imagen_sin_monto)
            if imagen_digito is None:
                return {'success': False, 'error': 'No se pudo cargar la imagen sin-monto.jpg'}
            
            # Posiciones fijas para sin monto
            posiciones_sin_monto = {
                'protecta': {'x': 938, 'y': 1772},
                'positiva': {'x': 824, 'y': 2116},
                # Positiva (Nueva): bloque blanco sobre el "S/. __" del nuevo layout.
                'positiva_nueva': {'x': 880, 'y': 1850}
            }
            
            x_posicion = posiciones_sin_monto[tipo_soat]['x']
            y_posicion = posiciones_sin_monto[tipo_soat]['y']
            
            # Verificar límites
            h_digito, w_digito = imagen_digito.shape[:2]
            h_fondo, w_fondo = fondo.shape[:2]
            
            if x_posicion + w_digito > w_fondo or y_posicion + h_digito > h_fondo:
                return {'success': False, 'error': 'La imagen sin-monto se sale de los límites del fondo'}
            
            # Pegar imagen sin monto
            resultado = fondo.copy()
            resultado[y_posicion:y_posicion+h_digito, x_posicion:x_posicion+w_digito] = imagen_digito
            
            # Guardar imagen final
            cv2.imwrite(archivo_salida, resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Generar PDF si está habilitado
            archivo_pdf = None
            if generar_pdf:
                pdf_path = archivo_salida.replace('.jpg', '.pdf')
                if self.convertir_imagen_a_pdf(archivo_salida, pdf_path):
                    archivo_pdf = pdf_path
            
            return {
                'success': True,
                'mensaje': f'SOAT {tipo_soat.upper()} procesado correctamente SIN MONTO',
                'tipo_soat': tipo_soat,
                'imagen_origen': 'sin-monto.jpg (posición fija)',
                'posicion_pegado': f'({x_posicion},{y_posicion})',
                'dimensiones_finales': f'{resultado.shape[1]}x{resultado.shape[0]}',
                'archivo_salida': archivo_salida,
                'archivo_pdf': archivo_pdf,
                'imagen_resultado': resultado,
                'identificador_detectado': identificador_detectado,  # AGREGAR ESTA LÍNEA
                'identificador_usado': 'automatico' if identificador_detectado else 'manual'  # AGREGAR ESTA LÍNEA
            }
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error procesando SOAT sin monto: {str(e)}")
            return {'success': False, 'error': f'Error procesando SOAT sin monto: {str(e)}'}

    def detectar_identificador_automatico(self, imagen: np.ndarray, tipo_soat: str) -> str:
        """
        Detecta automáticamente el identificador del vehículo en la imagen procesada
        
        Args:
            imagen: Imagen procesada en formato OpenCV (numpy array)
            tipo_soat: 'protecta' o 'positiva' para determinar región de búsqueda
            
        Returns:
            str: Identificador detectado o cadena vacía si no se encuentra
        """
        try:
            self.log_with_timestamp("STEP", f"Iniciando detección automática de identificador para {tipo_soat}")
            
            # Definir regiones de búsqueda según el tipo de SOAT
            regiones_busqueda = {
                'protecta': [
                    {'x1': 36, 'y1': 1595, 'x2': 258, 'y2': 1670, 'descripcion': 'Región principal Protecta'},
                    {'x1': 22, 'y1': 1585, 'x2': 276, 'y2': 1684, 'descripcion': 'Región extendida Protecta'}
                ],
                'positiva': [
                    {'x1': 83, 'y1': 2005, 'x2': 316, 'y2': 2071, 'descripcion': 'Región principal Positiva'},
                    {'x1': 59, 'y1': 1992, 'x2': 341, 'y2': 2087, 'descripcion': 'Región extendida Positiva'}
                ],
                # Positiva (Nueva): placa "D0A250" medida en x~48-210, y~1705-1748.
                'positiva_nueva': [
                    {'x1': 40, 'y1': 1698, 'x2': 225, 'y2': 1758, 'descripcion': 'Región principal Positiva Nueva'},
                    {'x1': 28, 'y1': 1688, 'x2': 250, 'y2': 1770, 'descripcion': 'Región extendida Positiva Nueva'}
                ]
            }
            
            if tipo_soat not in regiones_busqueda:
                self.log_with_timestamp("ERROR", f"Tipo de SOAT no válido para detección: {tipo_soat}")
                return ""
            
            # Probar múltiples métodos de OCR
            identificadores_detectados = []
            
            for region in regiones_busqueda[tipo_soat]:
                self.log_with_timestamp("INFO", f"Analizando {region['descripcion']}")
                
                # Extraer región de la imagen
                x1, y1, x2, y2 = region['x1'], region['y1'], region['x2'], region['y2']
                region_imagen = imagen[y1:y2, x1:x2].copy()
                
                if region_imagen.size == 0:
                    continue
                
                # OCR con Tesseract
                try:
                    texto_tesseract = self._extraer_texto_tesseract(region_imagen)
                    if texto_tesseract:
                        identificadores_detectados.extend(self._procesar_texto_ocr(texto_tesseract, "Tesseract"))
                except Exception as e:
                    self.log_with_timestamp("WARNING", f"Error con Tesseract: {e}")

            # Seleccionar el mejor identificador detectado
            mejor_identificador = self._seleccionar_mejor_identificador(identificadores_detectados)
            
            if mejor_identificador:
                self.log_with_timestamp("OK", f"Identificador detectado automáticamente: {mejor_identificador}")
                return mejor_identificador
            else:
                self.log_with_timestamp("WARNING", "No se pudo detectar identificador automáticamente")
                return ""
                
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error en detección automática: {e}")
            return ""

    def _extraer_texto_tesseract(self, region_imagen: np.ndarray) -> str:
        """Extrae texto usando Tesseract OCR"""
        try:
            # Preprocesar imagen para mejor OCR
            imagen_procesada = self._preprocesar_imagen_ocr(region_imagen)
            
            # Configurar Tesseract
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            
            # Extraer texto
            texto = pytesseract.image_to_string(imagen_procesada, config=config)
            return texto.strip()
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error Tesseract: {e}")
            return ""

    def _preprocesar_imagen_ocr(self, imagen: np.ndarray) -> np.ndarray:
        """Preprocesa imagen para mejorar la detección OCR"""
        try:
            # Convertir a escala de grises
            if len(imagen.shape) == 3:
                gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
            else:
                gris = imagen.copy()
            
            # Aplicar filtro gaussiano para reducir ruido
            suavizado = cv2.GaussianBlur(gris, (3, 3), 0)
            
            # Aplicar umbralización adaptativa
            umbral = cv2.adaptiveThreshold(suavizado, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
            
            # Dilatación para conectar caracteres fragmentados
            kernel = np.ones((2, 2), np.uint8)
            dilatado = cv2.dilate(umbral, kernel, iterations=1)
            
            return dilatado
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error preprocesando imagen OCR: {e}")
            return imagen

    def _procesar_texto_ocr(self, texto: str, metodo: str) -> list:
        """Procesa texto extraído por OCR y extrae posibles identificadores"""
        identificadores = []
        
        try:
            # Limpiar texto
            texto_limpio = re.sub(r'[^A-Za-z0-9\s]', '', texto.upper())
            
            # Patrones comunes de identificadores de vehículos
            patrones = [
                r'\b[A-Z]{3}\d{3}\b',      # ABC123
                r'\b[A-Z]{2}\d{4}\b',      # AB1234
                r'\b[A-Z]\d{5}\b',         # A12345
                r'\b\d{6}\b',              # 123456
                r'\b[A-Z]{3}\d{2}[A-Z]\b', # ABC12D
                r'\b[A-Z]\d{3}[A-Z]{2}\b'  # A123BC
            ]
            
            for patron in patrones:
                matches = re.findall(patron, texto_limpio)
                for match in matches:
                    if len(match) >= 4:  # Mínimo 4 caracteres
                        identificadores.append({
                            'texto': match,
                            'metodo': metodo,
                            'longitud': len(match),
                            'confianza': 0.8 if len(match) >= 6 else 0.6
                        })
            
            self.log_with_timestamp("INFO", f"{metodo} detectó {len(identificadores)} posibles identificadores")
            return identificadores
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error procesando texto OCR: {e}")
            return []

    def _seleccionar_mejor_identificador(self, identificadores: list) -> str:
        """Selecciona el mejor identificador de la lista de candidatos"""
        try:
            if not identificadores:
                return ""
            
            # Ordenar por confianza y longitud
            identificadores_ordenados = sorted(identificadores, 
                                             key=lambda x: (x['confianza'], x['longitud']), 
                                             reverse=True)
            
            # Seleccionar el mejor
            mejor = identificadores_ordenados[0]
            
            self.log_with_timestamp("INFO", f"Mejor candidato: {mejor['texto']} (confianza: {mejor['confianza']}, método: {mejor['metodo']})")
            
            return mejor['texto']
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error seleccionando mejor identificador: {e}")
            return ""


if __name__ == "__main__":
    # La lógica se ejecuta a través del servidor Flask (recepcion_imagen.py).
    SOATProcessor()
    print("Editor SOAT - Sistema de procesamiento de documentos")
    print("Sistema listo para procesar documentos")