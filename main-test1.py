import cv2

from pdf2image import convert_from_path
import numpy as np
# Convierte todas las páginas a imágenes
archivo_protecta = "Imagen-prueba-Protecta.pdf"
archivo_positiva = "Imagen-prueba-Positiva.pdf"

page_protecta = convert_from_path(archivo_protecta, dpi=300, poppler_path="poppler/poppler-24.02.0/Library/bin")
page_positiva = convert_from_path(archivo_positiva, dpi=300, poppler_path="poppler/poppler-24.02.0/Library/bin")

# Guardar cada página como PNG
for i, page in enumerate(page_protecta):
    page.save(f"final_protecta{i+1}.png", "PNG")

for i, page in enumerate(page_positiva):
    page.save(f"final_positiva{i+1}.png", "PNG")

###
# Cargar imágenes
"""
fondo = cv2.imread("final_protecta1.png")   # Imagen base
pegada = cv2.imread("prueba-cambio-soat.jpeg")  # Imagen a pegar

# Coordenadas donde pegar (esquina superior izquierda en la base)
x, y = 100, 50  

# Obtener dimensiones de la imagen a pegar
h, w = pegada.shape[:2]

# Colocar la imagen pegada sobre el fondo
fondo[y:y+h, x:x+w] = pegada

# Guardar o mostrar resultado
cv2.imwrite("resultado.jpg", fondo)
cv2.imshow("Resultado", fondo)
cv2.waitKey(0)
cv2.destroyAllWindows()
"""

# Cargar imágenes
fondo = cv2.imread("final_protecta1.png")
pegada = cv2.imread("monto-soles-170.png")

# Redimensionar la imagen pegada (hacerla más grande)

nuevo_ancho = 138  # 3.5 veces más ancha
nuevo_alto = 47   # 3.4 veces más alta
pegada_redimensionada = cv2.resize(pegada, (nuevo_ancho, nuevo_alto))

if nuevo_ancho >= 138 or nuevo_alto >= 47:
        # Obtener dimensiones
    h_fondo, w_fondo = fondo.shape[:2]
#h_pegada_redimensionada, w_pegada_redimensionada = pegada_redimensionada.shape[:2]
    h_pegada_redimensionada, w_pegada_redimensionada = pegada_redimensionada.shape[:2]

    print(f"Fondo: {w_fondo}x{h_fondo}")
    print(f"Pegada: {w_pegada_redimensionada}x{h_pegada_redimensionada}")

# Coordenadas donde pegar
    x, y = 860, 1728 

# Verificar que las coordenadas están dentro de los límites
    if x + w_pegada_redimensionada > w_fondo or y + h_pegada_redimensionada > h_fondo:
        print("Error: La imagen a pegar se sale de los límites del fondo")
        exit()

# Crear una copia del fondo para no modificar el original
    resultado = fondo.copy()

# Colocar la imagen pegada sobre el fondo
    resultado[y:y+h_pegada_redimensionada, x:x+w_pegada_redimensionada] = pegada_redimensionada

# Guardar resultado
    cv2.imwrite("resultado.jpg", resultado)
    exit()



# Verificar que las imágenes se cargaron correctamente
if fondo is None or pegada is None:
    print("Error: No se pudieron cargar las imágenes")
    exit()

else:
# Obtener dimensiones
    h_fondo, w_fondo = fondo.shape[:2]
#h_pegada_redimensionada, w_pegada_redimensionada = pegada_redimensionada.shape[:2]
    h_pegada, w_pegada = pegada.shape[:2]

    print(f"Fondo: {w_fondo}x{h_fondo}")
    print(f"Pegada: {w_pegada}x{h_pegada}")

# Coordenadas donde pegar
    x, y = 860, 1728 

# Verificar que las coordenadas están dentro de los límites
    if x + w_pegada > w_fondo or y + h_pegada > h_fondo:
        print("Error: La imagen a pegar se sale de los límites del fondo")
        exit()

# Crear una copia del fondo para no modificar el original
    resultado = fondo.copy()

# Colocar la imagen pegada sobre el fondo
    resultado[y:y+h_pegada, x:x+w_pegada] = pegada

# Guardar resultado
    cv2.imwrite("resultado.jpg", resultado)
    exit()