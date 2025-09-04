import cv2
from pdf2image import convert_from_path
import numpy as np
import os
import glob
from typing import Tuple, Optional, List
import shutil
from PIL import Image  # Agregar PIL para conversión a PDF

class SOATProcessor:
    def __init__(self):
        # Rutas de archivos de referencia
        self.archivo_protecta = "Imagen-prueba-Protecta.pdf"
        self.archivo_positiva = "Imagen-prueba-Positiva.pdf"
        
        # Configuración de poppler
        self.poppler_path = "poppler/poppler-24.02.0/Library/bin"
        
        # Extensiones de imagen soportadas
        self.extensiones_imagen = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        
        # Coordenadas y dimensiones por defecto para cada tipo de SOAT
        self.configuracion = {
            'protecta': {
                'x': 940, 'y': 1771
            },
            'positiva': {
                'x': 940, 'y': 1771
            }
        }
    
    def buscar_imagen_por_numero(self, numero: str) -> Optional[str]:
        """
        Busca una imagen en el sistema que contenga el numero en su nombre
        
        Args:
            numero: El numero a buscar en los nombres de archivo
            
        Returns:
            str: Ruta de la imagen encontrada o None si no se encuentra
        """
        directorios_busqueda = [".", "assets", "imagenes", "recursos"]
        
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
                    
                    if es_imagen and numero in archivo:
                        return ruta_completa
                        
            except Exception as e:
                continue
        
        return None
    
    def listar_imagenes_disponibles(self) -> List[dict]:
        """
        Lista todas las imagenes disponibles en el sistema con sus numeros extraidos
        """
        imagenes_info = []
        directorios_busqueda = [".", "assets", "imagenes", "recursos"]
        
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
                    
                    if es_imagen:
                        numeros = self.extraer_numeros_del_nombre(archivo)
                        
                        if numeros:  # Solo agregar si tiene numeros
                            imagen_info = {
                                'ruta': ruta_completa,
                                'nombre': archivo,
                                'numeros': numeros,
                                'tamano': os.path.getsize(ruta_completa),
                                'directorio': directorio
                            }
                            imagenes_info.append(imagen_info)
                        
            except Exception as e:
                continue
        
        return imagenes_info
    
    def extraer_numeros_del_nombre(self, nombre_archivo: str) -> List[str]:
        """
        Extrae todos los numeros de un nombre de archivo
        
        Args:
            nombre_archivo: Nombre del archivo
            
        Returns:
            List[str]: Lista de numeros encontrados
        """
        import re
        try:
            # Buscar secuencias de digitos (incluyendo decimales)
            patron = r'\d+(?:\.\d+)?'
            numeros = re.findall(patron, nombre_archivo)
            
            # Tambien buscar numeros que puedan estar separados por guiones o puntos
            # Por ejemplo: "monto-soles-170.png" deberia encontrar "170"
            patron_complejo = r'(?:^|[^\d])(\d+(?:\.\d+)?)(?=[^\d]|$)'
            numeros_complejos = re.findall(patron_complejo, nombre_archivo)
            
            # Combinar ambas busquedas y eliminar duplicados
            todos_numeros = list(set(numeros + numeros_complejos))
            
            return todos_numeros
            
        except Exception as e:
            print(f"Error extrayendo numeros de {nombre_archivo}: {e}")
            return []
    
    def validar_numero(self, numero_str: str) -> bool:
        """
        Valida que el string sea un numero valido
        
        Args:
            numero_str: String a validar
            
        Returns:
            bool: True si es un numero valido
        """
        try:
            # Verificar que solo contenga digitos y puntos/comas
            caracteres_validos = set('0123456789.,')
            if not all(c in caracteres_validos for c in numero_str):
                return False
            
            # Intentar convertir a float para validar formato
            float(numero_str.replace(',', '.'))
            return True
        except:
            return False
    
    def descomponer_numero_en_digitos(self, numero: str) -> List[str]:
        """
        Descompone un número en sus dígitos individuales
        
        Args:
            numero: Número como string (ej: "25", "123")
            
        Returns:
            List[str]: Lista de dígitos individuales (ej: ["2", "5"], ["1", "2", "3"])
        """
        try:
            # Limpiar el número (remover decimales si los hay)
            numero_limpio = numero.replace('.', '').replace(',', '')
            
            # Validar que solo contenga dígitos
            if not numero_limpio.isdigit():
                return []
            
            # Validar longitud máxima (3 dígitos)
            if len(numero_limpio) > 3:
                print(f"[WARNING] Número {numero} tiene más de 3 dígitos, truncando a los primeros 3")
                numero_limpio = numero_limpio[:3]
            
            # Descomponer en dígitos individuales
            digitos = list(numero_limpio)
            
            print(f"[INFO] Número {numero} descompuesto en dígitos: {digitos}")
            return digitos
            
        except Exception as e:
            print(f"[ERROR] Error descomponiendo número {numero}: {e}")
            return []

    def buscar_imagenes_por_digitos(self, digitos: List[str]) -> tuple:
        """
        Busca imágenes para cada dígito individual
        
        Args:
            digitos: Lista de dígitos individuales
            
        Returns:
            tuple: (imagenes_encontradas, digitos_no_encontrados)
        """
        imagenes_encontradas = []
        digitos_no_encontrados = []
        
        for i, digito in enumerate(digitos):
            ruta_imagen = self.buscar_imagen_por_numero(digito)
            
            if ruta_imagen:
                imagenes_encontradas.append({
                    'digito': digito,
                    'posicion': i,
                    'ruta': ruta_imagen,
                    'encontrada': True
                })
                print(f"[OK] Dígito {digito} encontrado en: {ruta_imagen}")
            else:
                digitos_no_encontrados.append(digito)
                imagenes_encontradas.append({
                    'digito': digito,
                    'posicion': i,
                    'ruta': None,
                    'encontrada': False
                })
                print(f"[ERROR] No se encontró imagen para el dígito {digito}")
        
        return imagenes_encontradas, digitos_no_encontrados

    def convertir_imagen_a_pdf(self, imagen_path: str, pdf_path: str) -> bool:
        """
        Convierte una imagen a formato PDF
        
        Args:
            imagen_path: Ruta de la imagen a convertir
            pdf_path: Ruta donde guardar el PDF
            
        Returns:
            bool: True si la conversión fue exitosa
        """
        try:
            # Abrir la imagen
            imagen = Image.open(imagen_path)
            
            # Convertir a RGB si es necesario (para compatibilidad con PDF)
            if imagen.mode != 'RGB':
                imagen = imagen.convert('RGB')
            
            # Guardar como PDF
            imagen.save(pdf_path, 'PDF', resolution=300.0, quality=95)
            
            print(f"[OK] Imagen convertida a PDF: {pdf_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error convirtiendo imagen a PDF: {e}")
            return False

    def procesar_soat_con_digitos(self, 
                                tipo_soat: str,
                                numero: str,
                                archivo_salida: str = "resultado.jpg",
                                aplicar_mejoras: bool = True,
                                factor_brillo: float = 1.5,
                                dpi_conversion: int = 300,
                                redimensionar_final: bool = False,
                                ancho_final: int = 1694,
                                alto_final: int = 3300,
                                generar_pdf: bool = True) -> dict:
        """
        NUEVA FUNCIONALIDAD: Procesa SOAT descomponiendo el número en dígitos individuales
        y pegando cada imagen en posiciones fijas predefinidas
        
        Args:
            tipo_soat: 'protecta' o 'positiva'
            numero: Número a procesar (máximo 3 dígitos)
            archivo_salida: Archivo de salida (JPG)
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
            print(f"[INFO] Iniciando procesamiento de SOAT con dígitos para número: {numero}")
            
            # 1. Validar y descomponer número
            if not self.validar_numero(numero):
                return {'success': False, 'error': 'El número ingresado no es válido.'}
            
            digitos = self.descomponer_numero_en_digitos(numero)
            if not digitos:
                return {'success': False, 'error': 'No se pudo descomponer el número en dígitos.'}
            
            # 2. Buscar imágenes para cada dígito
            imagenes_info, digitos_no_encontrados = self.buscar_imagenes_por_digitos(digitos)
            
            if digitos_no_encontrados:
                # Obtener números disponibles para mostrar error
                imagenes_disponibles = self.listar_imagenes_disponibles()
                numeros_disponibles = []
                for img in imagenes_disponibles:
                    numeros_disponibles.extend(img['numeros'])
                
                return {
                    'success': False, 
                    'error': f'No se encontraron imágenes para los dígitos: {", ".join(digitos_no_encontrados)}. Dígitos disponibles: {", ".join(set(numeros_disponibles))}'
                }
            
            # 3. Convertir PDF a imagen CON MEJORAS
            fondo = self.pdf_to_image_mejorada(tipo_soat, dpi_conversion, aplicar_mejoras, factor_brillo)
            if fondo is None:
                return {'success': False, 'error': f'No se pudo procesar el PDF de {tipo_soat}'}
            
            # 4. Redimensionar fondo si está habilitado
            dimensiones_originales = f'{fondo.shape[1]}x{fondo.shape[0]}'
            
            if redimensionar_final:
                print(f"[INFO] Redimensionando fondo a {ancho_final}x{alto_final} ANTES de pegar...")
                fondo = self.redimensionar_resultado_final(fondo, ancho_final, alto_final)
                self.guardar_imagen_intermedia(fondo, "fondo_redimensionado", tipo_soat)
                
                # Aplicar saturación a región específica
                if aplicar_mejoras:
                    print("[INFO] Aplicando saturación a región específica del fondo...")
                    fondo = self.saturar_region_rectangulo(fondo, 35, 2525, 1661, 2780, 1.6)
                    self.guardar_imagen_intermedia(fondo, "fondo_region_saturada", tipo_soat)
            
            # 5. Configuración de posiciones fijas para cada dígito
            posiciones_digitos = {
                'protecta': {
                    0: {'x': 940, 'y': 1771},   # Primer dígito (más a la izquierda)
                    1: {'x': 1000, 'y': 1771},  # Segundo dígito (centro)
                    2: {'x': 1060, 'y': 1771}   # Tercer dígito (más a la derecha)
                },
                'positiva': {
                    0: {'x': 940, 'y': 1771},   # Primer dígito (más a la izquierda)
                    1: {'x': 1000, 'y': 1771},  # Segundo dígito (centro)
                    2: {'x': 1060, 'y': 1771}   # Tercer dígito (más a la derecha)
                }
            }
            
            # 6. Procesar cada dígito en su posición fija
            resultado = fondo.copy()
            imagenes_pegadas = []
            
            for img_info in imagenes_info:
                if not img_info['encontrada']:
                    continue
                
                # Cargar imagen del dígito
                imagen_digito = cv2.imread(img_info['ruta'])
                if imagen_digito is None:
                    print(f"[ERROR] No se pudo cargar la imagen: {img_info['ruta']}")
                    continue
                
                # Guardar imagen intermedia
                self.guardar_imagen_intermedia(imagen_digito, f"digito_{img_info['digito']}_original", tipo_soat)
                
                # Obtener posición fija para este dígito
                posicion_digito = img_info['posicion']
                if posicion_digito not in posiciones_digitos[tipo_soat]:
                    print(f"[ERROR] No hay posición definida para el dígito en posición {posicion_digito}")
                    continue
                
                x_posicion = posiciones_digitos[tipo_soat][posicion_digito]['x']
                y_posicion = posiciones_digitos[tipo_soat][posicion_digito]['y']
                
                # Verificar límites
                h_digito, w_digito = imagen_digito.shape[:2]
                h_fondo, w_fondo = resultado.shape[:2]
                
                print(f"[INFO] Pegando dígito {img_info['digito']} de {w_digito}x{h_digito} en posición fija ({x_posicion},{y_posicion})")
                
                if x_posicion + w_digito > w_fondo or y_posicion + h_digito > h_fondo:
                    print(f"[ERROR] Dígito {img_info['digito']} se sale de los límites. Fondo: {w_fondo}x{h_fondo}")
                    continue
                
                # Pegar imagen del dígito en posición fija
                resultado[y_posicion:y_posicion+h_digito, x_posicion:x_posicion+w_digito] = imagen_digito
                
                imagenes_pegadas.append({
                    'digito': img_info['digito'],
                    'posicion': img_info['posicion'],
                    'coordenadas_fijas': f'({x_posicion},{y_posicion})',
                    'dimensiones': f'{w_digito}x{h_digito}'
                })
                
                print(f"[OK] Dígito {img_info['digito']} pegado en posición fija ({x_posicion},{y_posicion})")
            
            # 7. Guardar imagen intermedia del resultado
            self.guardar_imagen_intermedia(resultado, "resultado_final_con_digitos", tipo_soat)
            
            # 8. Guardar resultado final como JPG
            cv2.imwrite(archivo_salida, resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # 9. NUEVO: Generar PDF si está habilitado
            archivo_pdf = None
            if generar_pdf:
                pdf_path = archivo_salida.replace('.jpg', '.pdf')
                if self.convertir_imagen_a_pdf(archivo_salida, pdf_path):
                    archivo_pdf = pdf_path
                    print(f"[OK] PDF generado: {pdf_path}")
                else:
                    print(f"[WARNING] No se pudo generar el PDF")
            
            return {
                'success': True,
                'mensaje': f'SOAT {tipo_soat.upper()} procesado correctamente con número: {numero} (descompuesto en {len(digitos)} dígitos)',
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
                'archivo_pdf': archivo_pdf,  # NUEVO: Ruta del PDF generado
                'imagen_resultado': resultado
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Error interno procesando dígitos: {str(e)}'}
    
    def actualizar_archivo_pdf(self, tipo_soat: str, nuevo_archivo_path: str) -> bool:
        """
        Actualiza el archivo PDF de referencia (protecta o positiva)
        
        Args:
            tipo_soat: 'protecta' o 'positiva'
            nuevo_archivo_path: Ruta del nuevo archivo PDF
            
        Returns:
            bool: True si se actualizó correctamente
        """
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
            print(f"Error actualizando archivo {tipo_soat}: {e}")
            return False
    
    def pdf_to_image(self, tipo_soat: str, dpi: int = 300, aplicar_mejoras: bool = True) -> Optional[np.ndarray]:
        """
        Convierte PDF a imagen y la guarda como PNG (version simplificada para compatibilidad)
        """
        return self.pdf_to_image_mejorada(tipo_soat, dpi, aplicar_mejoras, 1.15, 'bilateral')

    def guardar_imagen_intermedia(self, imagen: np.ndarray, nombre_funcion: str, tipo_soat: str) -> str:
        """
        Guarda una imagen intermedia con el nombre de la funcion aplicada
        
        Args:
            imagen: Imagen en formato OpenCV
            nombre_funcion: Nombre de la funcion que se aplico
            tipo_soat: Tipo de SOAT para incluir en el nombre
            
        Returns:
            str: Ruta del archivo guardado
        """
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"{tipo_soat}_{nombre_funcion}_{timestamp}.png"
            ruta_archivo = os.path.join("imagenes_intermedias", nombre_archivo)
            
            # Crear carpeta si no existe
            os.makedirs("imagenes_intermedias", exist_ok=True)
            
            # Guardar imagen
            cv2.imwrite(ruta_archivo, imagen)
            print(f"[SAVE] Imagen guardada: {nombre_archivo}")
            
            return ruta_archivo
            
        except Exception as e:
            print(f"[ERROR] Error guardando imagen intermedia: {e}")
            return ""

    def pdf_to_image_mejorada(self, tipo_soat: str, dpi: int = 300, aplicar_mejoras: bool = True, 
                             factor_brillo: float = 1.5) -> Optional[np.ndarray]:
        """
        Convierte PDF a imagen con mejoras configurables
        """
        try:
            if tipo_soat == 'protecta':
                archivo_pdf = self.archivo_protecta
                archivo_png = "final_protecta1.png"
            elif tipo_soat == 'positiva':
                archivo_pdf = self.archivo_positiva
                archivo_png = "final_positiva1.png"
            else:
                raise ValueError("tipo_soat debe ser 'protecta' o 'positiva'")
            
            if not os.path.exists(archivo_pdf):
                raise FileNotFoundError(f"No se encuentra el archivo: {archivo_pdf}")
            
            # Convertir PDF a imagen
            pages = convert_from_path(archivo_pdf, dpi=dpi, poppler_path=self.poppler_path)
            page = pages[0]  # Tomar la primera pagina
            
            # Convertir a formato OpenCV
            imagen_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
            
            # Guardar imagen original del PDF
            self.guardar_imagen_intermedia(imagen_cv, "pdf_original", tipo_soat)
            
            # Aplicar mejoras si esta habilitado
            if aplicar_mejoras:
                print(f"[INFO] Aplicando mejoras a la imagen PDF (brillo: {factor_brillo})...")
                
                # Solo aumentar brillo, NO quitar texto traslucido
                imagen_cv = self.aumentar_brillo(imagen_cv, factor_brillo=factor_brillo)
                self.guardar_imagen_intermedia(imagen_cv, "aumentar_brillo", tipo_soat)
            
            # Guardar como PNG (version final)
            cv2.imwrite(archivo_png, imagen_cv)
            self.guardar_imagen_intermedia(imagen_cv, "resultado_final", tipo_soat)
            
            return imagen_cv
            
        except Exception as e:
            print(f"Error convirtiendo PDF a imagen: {e}")
            return None
    
    def restaurar_archivos_backup(self) -> dict:
        """
        Restaura los archivos PDF desde los backups
        
        Returns:
            dict: Estado de la restauracion
        """
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

    def aumentar_brillo(self, imagen: np.ndarray, factor_brillo: float = 1.5) -> np.ndarray:
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

    def procesar_soat_con_numero(self, 
                                tipo_soat: str,
                                numero: str,
                                archivo_salida: str = "resultado.jpg",
                                aplicar_mejoras: bool = True,
                                factor_brillo: float = 1.5,
                                dpi_conversion: int = 300,
                                redimensionar_final: bool = False,
                                ancho_final: int = 1694,
                                alto_final: int = 3300) -> dict:
        """
        NUEVO ORDEN DE OPERACIONES:
        1. Convertir PDF a imagen
        2. Aplicar mejoras al fondo
        3. Redimensionar fondo SI está habilitado
        4. Pegar imagen del número en coordenadas fijas
        """
        try:
            # 1-2. Validar numero y buscar imagen (igual que antes)
            if not self.validar_numero(numero):
                return {'success': False, 'error': 'El numero ingresado no es valido.'}
            
            ruta_imagen_numero = self.buscar_imagen_por_numero(numero)
            if not ruta_imagen_numero:
                imagenes_disponibles = self.listar_imagenes_disponibles()
                numeros_disponibles = []
                for img in imagenes_disponibles:
                    numeros_disponibles.extend(img['numeros'])
                
                return {
                    'success': False,
                    'error': f'No se encontro ninguna imagen con el numero {numero}. Numeros disponibles: {", ".join(set(numeros_disponibles))}'
                }
            
            # 3. Convertir PDF a imagen CON MEJORAS
            fondo = self.pdf_to_image_mejorada(tipo_soat, dpi_conversion, aplicar_mejoras, factor_brillo)
            if fondo is None:
                return {'success': False, 'error': f'No se pudo procesar el PDF de {tipo_soat}'}
            
            # 4. NUEVO: Redimensionar fondo ANTES de pegar
            dimensiones_originales = f'{fondo.shape[1]}x{fondo.shape[0]}'
            
            if redimensionar_final:
                print(f"[INFO] Redimensionando fondo a {ancho_final}x{alto_final} ANTES de pegar...")
                fondo = self.redimensionar_resultado_final(fondo, ancho_final, alto_final)
                self.guardar_imagen_intermedia(fondo, "fondo_redimensionado", tipo_soat)
                
                # NUEVO: Aplicar saturacion a region especifica DESPUES del redimensionamiento
                if aplicar_mejoras:
                    print("[INFO] Aplicando saturacion a region especifica del fondo...")
                    # Coordenadas especificas para la region a saturar (ajustar segun necesites)
                    fondo = self.saturar_region_rectangulo(fondo, 35, 2525, 1661, 2780, 1.6)
                    self.guardar_imagen_intermedia(fondo, "fondo_region_saturada", tipo_soat)
            
            # 5. Cargar imagen del numero y aplicar mejora de brillo
            pegada = cv2.imread(ruta_imagen_numero)
            if pegada is None:
                return {'success': False, 'error': f'No se pudo cargar la imagen: {ruta_imagen_numero}'}

            self.guardar_imagen_intermedia(pegada, "imagen_numero_original", tipo_soat)

            # NUEVO: Aplicar brillo a la imagen a pegar (DESACTIVADO)
            if False:  # Cambiar de aplicar_mejoras a False
                print(f"[INFO] Aplicando mejora de brillo a imagen del numero con factor: {factor_brillo}")
                pegada = self.aumentar_brillo(pegada, factor_brillo=factor_brillo)
                self.guardar_imagen_intermedia(pegada, "imagen_numero_con_brillo", tipo_soat)
            
            # 6. Obtener coordenadas especificas (AHORA para imagen ya redimensionada)
            config = self.configuracion[tipo_soat]
            x = config['x']
            y = config['y']
            
            # 7. Verificar limites
            h_fondo, w_fondo = fondo.shape[:2]
            h_pegada, w_pegada = pegada.shape[:2]
            
            print(f"[INFO] Pegando imagen de {w_pegada}x{h_pegada} en posicion ({x},{y})")
            print(f"[DEBUG] Fondo final: {w_fondo}x{h_fondo}")
            
            if x + w_pegada > w_fondo or y + h_pegada > h_fondo:
                return {
                    'success': False,
                    'error': f'La imagen se sale de los limites. Fondo: {w_fondo}x{h_fondo}, Imagen: {w_pegada}x{h_pegada}'
                }
            
            # 8. Pegar imagen YA con brillo aplicado
            resultado = fondo.copy()
            resultado[y:y+h_pegada, x:x+w_pegada] = pegada
            self.guardar_imagen_intermedia(resultado, "resultado_final_con_numero", tipo_soat)
            
            # 9. Guardar resultado (SIN aplicar más mejoras al resultado final)
            cv2.imwrite(archivo_salida, resultado, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            return {
                'success': True,
                'mensaje': f'SOAT {tipo_soat.upper()} procesado correctamente con numero: {numero}',
                'tipo_soat': tipo_soat,
                'numero': numero,
                'ruta_imagen_usada': ruta_imagen_numero,
                'mejoras_aplicadas': aplicar_mejoras,
                'factor_brillo_usado': factor_brillo,
                'dpi_usado': dpi_conversion,
                'imagen_origen': 'encontrada en sistema',
                'dimensiones_originales': dimensiones_originales,
                'dimensiones_finales': f'{resultado.shape[1]}x{resultado.shape[0]}',
                'redimensionado': redimensionar_final,
                'posicion_pegado': f'({x},{y})',
                'archivo_salida': archivo_salida,
                'imagen_resultado': resultado
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Error interno: {str(e)}'}

def main():
    """Funcion principal para ejecutar directamente el script"""
    processor = SOATProcessor()
    
    # Mostrar imagenes disponibles
    print("Imagenes disponibles en el sistema:")
    imagenes = processor.listar_imagenes_disponibles()
    
    if imagenes:
        for img in imagenes:
            print(f"  [ARCHIVO] {img['nombre']} - Numeros encontrados: {img['numeros']}")
    else:
        print("  [ERROR] No se encontraron imagenes con numeros en el sistema")
    
    # Ejemplo de uso comentado
    """
    resultado = processor.procesar_soat_con_numero(
        tipo_soat='protecta',
        numero='170'
    )
    
    if resultado['success']:
        print(f"[OK] {resultado['mensaje']}")
        print(f"[INFO] Imagen usada: {resultado['ruta_imagen_usada']}")
    else:
        print(f"[ERROR] Error: {resultado['error']}")
    """

if __name__ == "__main__":
    main()