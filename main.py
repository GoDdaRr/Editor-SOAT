import cv2
from pdf2image import convert_from_path
import numpy as np
import os
import glob
from typing import Tuple, Optional, List
import shutil
from PIL import Image
import platform
import datetime

class SOATProcessor:
    def __init__(self):
        # Rutas de archivos de referencia
        self.archivo_protecta = "Imagen-prueba-Protecta.pdf"
        self.archivo_positiva = "Imagen-prueba-Positiva.pdf"
        
        # Configuración de poppler
        sistema = platform.system().lower()
        
        if sistema == "windows":
            self.poppler_path = os.path.abspath("poppler/poppler-24.02.0/Library/bin")
            if not os.path.exists(self.poppler_path):
                self.poppler_path = None
        else:
            self.poppler_path = "/usr/bin"
            if not os.path.exists(os.path.join(self.poppler_path, "pdftoppm")):
                self.poppler_path = None
        
        # Extensiones de imagen soportadas
        self.extensiones_imagen = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
    
    def log_with_timestamp(self, level: str, message: str):
        """Logging básico para producción"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if level in ['ERROR', 'WARNING']:
            print(f"[{timestamp}] [{level}] {message}")
    
    def buscar_imagen_por_numero(self, numero: str, tipo_soat: str = "protecta") -> Optional[str]:
        """Busca una imagen en el sistema que contenga el numero en su nombre"""
        if tipo_soat == "positiva":
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
                                archivo_salida: str = "resultado.jpg",
                                aplicar_mejoras: bool = True,
                                factor_brillo: float = 1.1,
                                dpi_conversion: int = 300,
                                redimensionar_final: bool = False,
                                ancho_final: int = 1694,
                                alto_final: int = 3300,
                                generar_pdf: bool = True) -> dict:
        """Procesa SOAT descomponiendo el número en dígitos individuales"""
        try:
            # Validar y descomponer número
            if not self.validar_numero(numero):
                return {'success': False, 'error': 'El número ingresado no es válido.'}
            
            digitos = self.descomponer_numero_en_digitos(numero)
            if not digitos:
                return {'success': False, 'error': 'No se pudo descomponer el número en dígitos.'}
            
            # Buscar imágenes para cada dígito
            imagenes_info, digitos_no_encontrados = self.buscar_imagenes_por_digitos(digitos, tipo_soat)
            
            if digitos_no_encontrados:
                return {
                    'success': False, 
                    'error': f'No se encontraron imágenes para los dígitos: {", ".join(digitos_no_encontrados)}'
                }
            
            # Convertir PDF a imagen
            fondo = self.pdf_to_image_mejorada(tipo_soat, dpi_conversion, aplicar_mejoras, factor_brillo)
            if fondo is None:
                return {'success': False, 'error': f'No se pudo procesar el PDF de {tipo_soat}'}
            
            # Redimensionar fondo si está habilitado
            dimensiones_originales = f'{fondo.shape[1]}x{fondo.shape[0]}'
            
            if redimensionar_final:
                fondo = self.redimensionar_resultado_final(fondo, ancho_final, alto_final)
                
                if aplicar_mejoras:
                    fondo = self.saturar_region_rectangulo(fondo, 35, 2525, 1661, 2780, 1.6)
            
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
                }
            }
            
            # Procesar cada dígito en su posición fija
            resultado = fondo.copy()
            imagenes_pegadas = []
            
            for img_info in imagenes_info:
                if not img_info['encontrada']:
                    continue
                
                imagen_digito = cv2.imread(img_info['ruta'])
                if imagen_digito is None:
                    continue
                
                posicion_digito = img_info['posicion']
                if posicion_digito not in posiciones_digitos[tipo_soat]:
                    continue
                
                x_posicion = posiciones_digitos[tipo_soat][posicion_digito]['x']
                y_posicion = posiciones_digitos[tipo_soat][posicion_digito]['y']
                
                h_digito, w_digito = imagen_digito.shape[:2]
                h_fondo, w_fondo = resultado.shape[:2]
                
                if x_posicion + w_digito > w_fondo or y_posicion + h_digito > h_fondo:
                    continue
                
                resultado[y_posicion:y_posicion+h_digito, x_posicion:x_posicion+w_digito] = imagen_digito
                
                imagenes_pegadas.append({
                    'digito': img_info['digito'],
                    'posicion': img_info['posicion'],
                    'coordenadas_fijas': f'({x_posicion},{y_posicion})',
                    'dimensiones': f'{w_digito}x{h_digito}'
                })
            
            # Guardar la imagen final
            cv2.imwrite(archivo_salida, resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Generar PDF si está habilitado
            archivo_pdf = None
            if generar_pdf:
                pdf_path = archivo_salida.replace('.jpg', '.pdf')
                if self.convertir_imagen_a_pdf(archivo_salida, pdf_path):
                    archivo_pdf = pdf_path
            
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
                'imagen_resultado': resultado
            }
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error interno procesando dígitos: {str(e)}")
            return {'success': False, 'error': f'Error interno procesando dígitos: {str(e)}'}
    
    def actualizar_archivo_pdf(self, tipo_soat: str, nuevo_archivo_path: str) -> bool:
        """Actualiza el archivo PDF de referencia"""
        try:
            if tipo_soat == 'protecta':
                if os.path.exists(self.archivo_protecta):
                    backup_path = f"{self.archivo_protecta}.backup"
                    shutil.copy2(self.archivo_protecta, backup_path)
                shutil.copy2(nuevo_archivo_path, self.archivo_protecta)
                
            elif tipo_soat == 'positiva':
                if os.path.exists(self.archivo_positiva):
                    backup_path = f"{self.archivo_positiva}.backup"
                    shutil.copy2(self.archivo_positiva, backup_path)
                shutil.copy2(nuevo_archivo_path, self.archivo_positiva)
            else:
                return False
            
            return True
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error actualizando archivo {tipo_soat}: {e}")
            return False
    
    def pdf_to_image_mejorada(self, tipo_soat: str, dpi: int = 300, aplicar_mejoras: bool = True, 
                             factor_brillo: float = 1.3) -> Optional[np.ndarray]:
        """Convierte PDF a imagen con mejoras configurables"""
        try:
            if tipo_soat == 'protecta':
                archivo_pdf = self.archivo_protecta
            elif tipo_soat == 'positiva':
                archivo_pdf = self.archivo_positiva
            else:
                raise ValueError("tipo_soat debe ser 'protecta' o 'positiva'")
            
            if not os.path.exists(archivo_pdf):
                raise FileNotFoundError(f"No se encuentra el archivo: {archivo_pdf}")
            
            if self.poppler_path is None:
                self.log_with_timestamp("ERROR", "Poppler no configurado correctamente")
                return None
            
            # Convertir PDF a imagen
            pages = convert_from_path(archivo_pdf, dpi=dpi, poppler_path=self.poppler_path)
            page = pages[0]
            
            # Convertir a formato OpenCV
            imagen_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
            
            # Aplicar mejoras si está habilitado
            if aplicar_mejoras:
                imagen_cv = self.aumentar_brillo(imagen_cv, factor_brillo=factor_brillo)
            
            return imagen_cv
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error convirtiendo PDF a imagen: {e}")
            return None

    def aumentar_brillo(self, imagen: np.ndarray, factor_brillo: float = 1.3) -> np.ndarray:
        """Aumenta el brillo de una imagen"""
        try:
            imagen_float = imagen.astype(np.float32)
            imagen_brillante = imagen_float * factor_brillo
            imagen_brillante = np.clip(imagen_brillante, 0, 255)
            return imagen_brillante.astype(np.uint8)
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error aumentando brillo: {e}")
            return imagen

    def redimensionar_resultado_final(self, imagen: np.ndarray, ancho_objetivo: int = 1694, alto_objetivo: int = 3300) -> np.ndarray:
        """Redimensiona la imagen final a un tamaño específico"""
        try:
            return cv2.resize(imagen, (ancho_objetivo, alto_objetivo), interpolation=cv2.INTER_CUBIC)
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error redimensionando imagen: {e}")
            return imagen

    def saturar_region_rectangulo(self, imagen: np.ndarray, x1: int, y1: int, x2: int, y2: int, 
                             factor_saturacion: float = 1.6) -> np.ndarray:
        """Satura una región rectangular específica"""
        try:
            resultado = imagen.copy()
            h_img, w_img = imagen.shape[:2]
            
            x_inicio = min(x1, x2)
            y_inicio = min(y1, y2)
            x_fin = max(x1, x2)
            y_fin = max(y1, y2)
            
            if x_inicio < 0 or y_inicio < 0 or x_fin >= w_img or y_fin >= h_img:
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
            
            return resultado
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error saturando región: {e}")
            return imagen

    def procesar_soat_sin_monto(self, 
                               tipo_soat: str,
                               archivo_salida: str = "resultado_sin_monto.jpg",
                               aplicar_mejoras: bool = True,
                               factor_brillo: float = 1.3,
                               dpi_conversion: int = 300,
                               redimensionar_final: bool = False,
                               ancho_final: int = 1694,
                               alto_final: int = 3300,
                               generar_pdf: bool = True) -> dict:
        """Procesa SOAT sin monto - solo pega la imagen sin-monto.jpg"""
        try:
            # Buscar imagen sin monto
            imagen_sin_monto = self.buscar_imagen_por_numero("sin-monto", tipo_soat)
            if not imagen_sin_monto:
                return {'success': False, 'error': 'No se encontró la imagen sin-monto.jpg'}
            
            # Convertir PDF a imagen
            fondo = self.pdf_to_image_mejorada(tipo_soat, dpi_conversion, aplicar_mejoras, factor_brillo)
            if fondo is None:
                return {'success': False, 'error': f'No se pudo procesar el PDF de {tipo_soat}'}
            
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
                'positiva': {'x': 824, 'y': 2116}
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
                'imagen_resultado': resultado
            }
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error procesando SOAT sin monto: {str(e)}")
            return {'success': False, 'error': f'Error procesando SOAT sin monto: {str(e)}'}

    def restaurar_archivos_backup(self) -> dict:
        """Restaura los archivos PDF desde los backups"""
        try:
            restaurados = []
            
            # Restaurar protecta
            backup_protecta = f"{self.archivo_protecta}.backup"
            if os.path.exists(backup_protecta):
                shutil.copy2(backup_protecta, self.archivo_protecta)
                restaurados.append('protecta')
            
            # Restaurar positiva
            backup_positiva = f"{self.archivo_positiva}.backup"
            if os.path.exists(backup_positiva):
                shutil.copy2(backup_positiva, self.archivo_positiva)
                restaurados.append('positiva')
            
            if restaurados:
                return {
                    'success': True,
                    'mensaje': f'Archivos restaurados: {", ".join(restaurados)}'
                }
            else:
                return {
                    'success': False,
                    'error': 'No hay archivos de backup disponibles'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error restaurando archivos: {str(e)}'
            }


    def aumentar_brillo(self, imagen: np.ndarray, factor_brillo: float = 1.3) -> np.ndarray:
        """
        Aumenta el brillo de una imagen
        
        Args:
            imagen: Imagen en formato OpenCV (numpy array)
            factor_brillo: Factor de aumento del brillo (1.0 = sin cambio, >1.0 = mas brillo)
            
        Returns:
            np.ndarray: Imagen con brillo aumentado
        """
        try:
            # Convertir a float para evitar overflow
            imagen_float = imagen.astype(np.float32)
            
            # Aplicar factor de brillo
            imagen_brillante = imagen_float * factor_brillo
            
            # Asegurar que los valores esten en el rango [0, 255]
            imagen_brillante = np.clip(imagen_brillante, 0, 255)
            
            # Convertir de vuelta a uint8
            imagen_resultado = imagen_brillante.astype(np.uint8)
            
            print(f"[OK] Brillo aumentado con factor: {factor_brillo}")
            return imagen_resultado
            
        except Exception as e:
            print(f"[ERROR] Error aumentando brillo: {e}")
            return imagen  # Retornar imagen original si hay error

    def redimensionar_resultado_final(self, imagen: np.ndarray, ancho_objetivo: int = 1694, alto_objetivo: int = 3300) -> np.ndarray:
        """
        Redimensiona la imagen final a un tamaño específico
        
        Args:
            imagen: Imagen en formato OpenCV (numpy array)
            ancho_objetivo: Ancho objetivo en pixeles (por defecto 1694)
            alto_objetivo: Alto objetivo en pixeles (por defecto 3300)
            
        Returns:
            np.ndarray: Imagen redimensionada al tamaño objetivo
        """
        try:
            alto_actual, ancho_actual = imagen.shape[:2]
            
            print(f"[INFO] Redimensionando imagen de {ancho_actual}x{alto_actual} a {ancho_objetivo}x{alto_objetivo}")
            
            # Redimensionar usando interpolación de alta calidad
            imagen_redimensionada = cv2.resize(imagen, (ancho_objetivo, alto_objetivo), interpolation=cv2.INTER_CUBIC)
            
            print(f"[OK] Imagen redimensionada correctamente")
            return imagen_redimensionada
            
        except Exception as e:
            print(f"[ERROR] Error redimensionando imagen: {e}")
            return imagen  # Retornar imagen original si hay error

    def saturar_region_rectangulo(self, imagen: np.ndarray, x1: int, y1: int, x2: int, y2: int, 
                                 factor_saturacion: float = 1.6) -> np.ndarray:
        """
        Satura una region rectangular definida por dos puntos especificos (x1,y1) y (x2,y2)
        Se aplica despues del redimensionamiento del fondo
        
        Args:
            imagen: Imagen en formato OpenCV (numpy array)
            x1: Coordenada X del punto inicial
            y1: Coordenada Y del punto inicial  
            x2: Coordenada X del punto final
            y2: Coordenada Y del punto final
            factor_saturacion: Factor de saturacion (1.0 = sin cambio, >1.0 = mas saturado)
            
        Returns:
            np.ndarray: Imagen con region saturada
        """
        try:
            resultado = imagen.copy()
            h_img, w_img = imagen.shape[:2]
            
            # Asegurar que x1,y1 sea el punto superior izquierdo
            x_inicio = min(x1, x2)
            y_inicio = min(y1, y2)
            x_fin = max(x1, x2)
            y_fin = max(y1, y2)
            
            # Validar que la region este dentro de los limites
            if x_inicio < 0 or y_inicio < 0 or x_fin >= w_img or y_fin >= h_img:
                print(f"[ERROR] Region fuera de limites. Imagen: {w_img}x{h_img}, Region: ({x_inicio},{y_inicio}) a ({x_fin},{y_fin})")
                return imagen
            
            # Extraer la region rectangular
            region = imagen[y_inicio:y_fin+1, x_inicio:x_fin+1].copy()
            
            # Convertir a HSV para manipular saturacion
            region_hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
            
            # Separar canales H, S, V
            h, s, v = cv2.split(region_hsv)
            
            # Aumentar saturacion (canal S)
            s_float = s.astype(np.float32)
            s_saturada = s_float * factor_saturacion
            
            # Asegurar que este en rango [0, 255]
            s_saturada = np.clip(s_saturada, 0, 255).astype(np.uint8)
            
            # Recombinar canales
            region_hsv_saturada = cv2.merge([h, s_saturada, v])
            
            # Convertir de vuelta a BGR
            region_saturada = cv2.cvtColor(region_hsv_saturada, cv2.COLOR_HSV2BGR)
            
            # Colocar la region saturada de vuelta en la imagen
            resultado[y_inicio:y_fin+1, x_inicio:x_fin+1] = region_saturada
            
            ancho = x_fin - x_inicio + 1
            alto = y_fin - y_inicio + 1
            
            print(f"[OK] Region saturada desde ({x_inicio},{y_inicio}) hasta ({x_fin},{y_fin}) - Tamano: {ancho}x{alto} pixeles")
            return resultado
            
        except Exception as e:
            print(f"[ERROR] Error saturando region: {e}")
            return imagen

    def procesar_soat_sin_monto(self, tipo_soat: str, archivo_salida: str, 
                                aplicar_mejoras: bool = True, factor_brillo: float = 1.3,
                                dpi_conversion: int = 300, redimensionar_final: bool = True,
                                ancho_final: int = 1694, alto_final: int = 3300,
                                generar_pdf: bool = True) -> dict:
        """
        Procesa el SOAT SIN monto - solo pega la imagen sin-monto.jpg en posición fija
        
        Args:
            tipo_soat: 'protecta' o 'positiva'
            archivo_salida: Ruta donde guardar la imagen resultado
            aplicar_mejoras: Aplicar mejoras de calidad
            factor_brillo: Factor de brillo
            dpi_conversion: DPI de conversión
            redimensionar_final: Redimensionar imagen final
            ancho_final: Ancho objetivo
            alto_final: Alto objetivo
            generar_pdf: Si generar también versión PDF
            
        Returns:
            dict: Resultado del procesamiento
        """
        try:
            self.log_with_timestamp("INFO", f"Iniciando procesamiento de SOAT sin monto para {tipo_soat}")
            
            # 1. Validar tipo de SOAT
            if tipo_soat not in ['protecta', 'positiva']:
                self.log_with_timestamp("ERROR", f"Tipo de SOAT inválido: {tipo_soat}")
                return {'success': False, 'error': 'Tipo de SOAT inválido. Use "protecta" o "positiva".'}
            
            # 2. Buscar imagen sin-monto.jpg
            imagen_sin_monto_path = "assets/sin-monto.jpg"
            if not os.path.exists(imagen_sin_monto_path):
                self.log_with_timestamp("ERROR", f"No se encontró la imagen: {imagen_sin_monto_path}")
                return {'success': False, 'error': f'No se encontró la imagen sin-monto.jpg en {imagen_sin_monto_path}'}
            
            # 3. Cargar imagen sin-monto.jpg
            self.log_with_timestamp("INFO", f"Cargando imagen sin-monto: {imagen_sin_monto_path}")
            imagen_sin_monto = cv2.imread(imagen_sin_monto_path)
            if imagen_sin_monto is None:
                self.log_with_timestamp("ERROR", f"No se pudo cargar la imagen: {imagen_sin_monto_path}")
                return {'success': False, 'error': f'No se pudo cargar la imagen sin-monto.jpg'}
            
            # 4. Convertir PDF a imagen CON MEJORAS (reutilizar función existente)
            self.log_with_timestamp("INFO", f"Convirtiendo PDF a imagen para {tipo_soat}")
            fondo = self.pdf_to_image_mejorada(tipo_soat, dpi_conversion, aplicar_mejoras, factor_brillo)
            if fondo is None:
                self.log_with_timestamp("ERROR", f"No se pudo procesar el PDF de {tipo_soat}")
                return {'success': False, 'error': f'No se pudo procesar el PDF de {tipo_soat}'}
            
            self.log_with_timestamp("INFO", f"PDF convertido exitosamente, dimensiones: {fondo.shape}")
            
            # 5. Redimensionar fondo si está habilitado (reutilizar función existente)
            dimensiones_originales = f'{fondo.shape[1]}x{fondo.shape[0]}'
            
            if redimensionar_final:
                self.log_with_timestamp("INFO", f"Redimensionando fondo a {ancho_final}x{alto_final}")
                fondo = self.redimensionar_resultado_final(fondo, ancho_final, alto_final)
                
                # Aplicar saturación a región específica (reutilizar función existente)
                if aplicar_mejoras:
                    self.log_with_timestamp("INFO", "Aplicando saturación a región específica del fondo...")
                    fondo = self.saturar_region_rectangulo(fondo, 35, 2525, 1661, 2780, 1.6)
            
            # 6. Configuración de posición fija para imagen sin-monto
            posiciones_sin_monto = {
                'protecta': {
                    'x': 840,   # Cambiar a zona diferente - más a la izquierda
                    'y': 1670   # Cambiar a zona diferente - más abajo
                },
                'positiva': {
                    'x': 824,   # Cambiar a zona diferente - más a la izquierda
                    'y': 2116   # Cambiar a zona diferente - más abajo
                }
            }

            x_posicion = posiciones_sin_monto[tipo_soat]['x']
            y_posicion = posiciones_sin_monto[tipo_soat]['y']
            self.log_with_timestamp("INFO", f"Usando coordenadas específicas para SIN MONTO: ({x_posicion}, {y_posicion})")

            # DEBUG: Información detallada antes del pegado
            self.log_with_timestamp("DEBUG", f"=== DEBUG ANTES DEL PEGADO SIN MONTO ===")
            self.log_with_timestamp("DEBUG", f"Función ejecutándose: procesar_soat_sin_monto")
            self.log_with_timestamp("DEBUG", f"Tipo SOAT: {tipo_soat}")
            self.log_with_timestamp("DEBUG", f"Coordenadas calculadas: ({x_posicion}, {y_posicion})")
            
            # 7. Verificar límites antes de pegar
            h_imagen, w_imagen = imagen_sin_monto.shape[:2]
            h_fondo, w_fondo = fondo.shape[:2]
            
            self.log_with_timestamp("DEBUG", f"Dimensiones imagen sin-monto: {w_imagen}x{h_imagen}")
            self.log_with_timestamp("DEBUG", f"Dimensiones fondo: {w_fondo}x{h_fondo}")
            self.log_with_timestamp("DEBUG", f"Área de pegado: desde ({x_posicion},{y_posicion}) hasta ({x_posicion+w_imagen},{y_posicion+h_imagen})")
            self.log_with_timestamp("DEBUG", f"=============================================")
            
            self.log_with_timestamp("INFO", f"Pegando imagen sin-monto de {w_imagen}x{h_imagen} en posición ({x_posicion},{y_posicion})")
            
            if x_posicion + w_imagen > w_fondo or y_posicion + h_imagen > h_fondo:
                self.log_with_timestamp("ERROR", f"Imagen sin-monto se sale de los límites. Fondo: {w_fondo}x{h_fondo}")
                return {'success': False, 'error': 'La imagen sin-monto se sale de los límites del fondo'}
            
            # 8. Crear copia del fondo y pegar imagen sin-monto
            resultado = fondo.copy()
            resultado[y_posicion:y_posicion+h_imagen, x_posicion:x_posicion+w_imagen] = imagen_sin_monto
            
            # 9. Guardar imagen intermedia del resultado
            self.log_with_timestamp("INFO", f"Guardando imagen final: {archivo_salida}")
            cv2.imwrite(archivo_salida, resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # 10. Guardar la imagen final
            self.log_with_timestamp("INFO", f"Guardando imagen final: {archivo_salida}")
            cv2.imwrite(archivo_salida, resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # 11. Generar PDF si está habilitado (reutilizar función existente)
            archivo_pdf = None
            if generar_pdf:
                pdf_path = archivo_salida.replace('.jpg', '.pdf')
                self.log_with_timestamp("INFO", f"Generando PDF: {pdf_path}")
                if self.convertir_imagen_a_pdf(archivo_salida, pdf_path):
                    archivo_pdf = pdf_path
                    self.log_with_timestamp("OK", f"PDF generado: {pdf_path}")
                else:
                    self.log_with_timestamp("WARNING", "No se pudo generar el PDF")
            
            self.log_with_timestamp("OK", f"Procesamiento sin monto completado exitosamente para {tipo_soat}")
            
            return {
                'success': True,
                'mensaje': f'SOAT {tipo_soat.upper()} procesado correctamente SIN MONTO',
                'tipo_soat': tipo_soat,
                'numero': 'SIN-MONTO',
                'imagen_pegada': 'sin-monto.jpg',
                'posicion_pegado': f'({x_posicion},{y_posicion})',
                'mejoras_aplicadas': aplicar_mejoras,
                'factor_brillo_usado': factor_brillo,
                'dpi_usado': dpi_conversion,
                'imagen_origen': 'sin-monto.jpg (posición fija)',
                'dimensiones_originales': dimensiones_originales,
                'dimensiones_finales': f'{resultado.shape[1]}x{resultado.shape[0]}',
                'redimensionado': redimensionar_final,
                'archivo_salida': archivo_salida,
                'archivo_pdf': archivo_pdf,
                'imagen_resultado': resultado  # Esta es la imagen que se usará para todo
            }
            
        except Exception as e:
            self.log_with_timestamp("ERROR", f"Error interno procesando sin monto: {str(e)}")
            import traceback
            self.log_with_timestamp("ERROR", f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': f'Error interno procesando sin monto: {str(e)}'}

def main():
    """Funcion principal para ejecutar directamente el script"""
    processor = SOATProcessor()
    
    # Mostrar imagenes disponibles por tipo
    processor.mostrar_imagenes_disponibles_por_tipo()
    
    # Ejemplo de uso comentado
    """
    resultado = processor.procesar_soat_con_digitos(
        tipo_soat='protecta',
        numero='170'
    )
    
    if resultado['success']:
        print(f"[OK] {resultado['mensaje']}")
        print(f"[INFO] Imagen usada: {resultado['imagen_origen']}")
    else:
        print(f"[ERROR] Error: {resultado['error']}")
    """

if __name__ == "__main__":
    # Solo mostrar información básica en producción
    processor = SOATProcessor()
    print("Editor SOAT - Sistema de procesamiento de documentos")
    print("Sistema listo para procesar documentos")