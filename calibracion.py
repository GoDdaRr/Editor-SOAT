"""
Herramienta de calibración de coordenadas para Editor SOAT.

Renderiza un PDF con EXACTAMENTE el mismo pipeline que la app
(conversión a 300 DPI, brillo, redimensión a 1694x3300 y saturación de
región) y dibuja encima una cuadrícula con coordenadas. Sirve para leer
con precisión dónde hay que pegar los dígitos del monto y dónde está la
placa, sin tener que adivinar.

Uso:
    python calibracion.py "ruta/al/nuevo.pdf"
    python calibracion.py "ruta/al/nuevo.pdf" salida.jpg

Luego abre la imagen generada y anota:
  - (x, y) de la esquina SUPERIOR-IZQUIERDA donde debe ir el primer dígito
    del monto (justo después de "S/. "). Los siguientes dígitos van a la
    misma 'y', separados ~36 px en 'x'.
  - El rectángulo (x1,y1)-(x2,y2) que rodea la placa (para el OCR).

Esos valores se colocan en main.py:
  posiciones_digitos['positiva_nueva'], posiciones_sin_monto['positiva_nueva']
  y regiones_busqueda['positiva_nueva'].
"""
import sys
import cv2
from main import SOATProcessor

ANCHO_FINAL = 1694
ALTO_FINAL = 3300


def generar_calibracion(pdf_path: str, salida: str = "calibracion.jpg") -> bool:
    proc = SOATProcessor()

    # Mismo pipeline que la app, pero SIN pegar dígitos.
    fondo = proc.pdf_to_image_mejorada(pdf_path, dpi=300, aplicar_mejoras=True, factor_brillo=1.15)
    if fondo is None:
        print("[x] No se pudo convertir el PDF. Verifica que Poppler esté instalado.")
        return False

    fondo = proc.redimensionar_resultado_final(fondo, ANCHO_FINAL, ALTO_FINAL)
    fondo = proc.saturar_region_rectangulo(fondo, 35, 2525, 1661, 2780, 1.6)

    img = fondo.copy()
    h, w = img.shape[:2]

    # Cuadrícula: líneas verdes cada 100 px, rojas (gruesas + etiqueta) cada 500 px.
    for x in range(0, w, 100):
        es_principal = (x % 500 == 0)
        color = (0, 0, 255) if es_principal else (0, 200, 0)
        cv2.line(img, (x, 0), (x, h), color, 2 if es_principal else 1)
        if es_principal:
            cv2.putText(img, str(x), (x + 3, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    for y in range(0, h, 100):
        es_principal = (y % 500 == 0)
        color = (0, 0, 255) if es_principal else (0, 200, 0)
        cv2.line(img, (0, y), (w, y), color, 2 if es_principal else 1)
        if es_principal:
            cv2.putText(img, str(y), (5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imwrite(salida, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"[+] Imagen de calibración guardada en: {salida} ({w}x{h})")
    print("[i] Abre la imagen, lee las coordenadas en la cuadrícula y ajusta main.py.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python calibracion.py <archivo.pdf> [salida.jpg]")
        sys.exit(1)

    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "calibracion.jpg"
    generar_calibracion(pdf, out)
