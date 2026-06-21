# Editor SOAT

Aplicación web (Flask) para editar documentos SOAT de las aseguradoras **Protecta** y
**Positiva**. Toma el PDF SOAT que sube el usuario, estampa sobre él el monto (compuesto
dígito a dígito a partir de imágenes pregeneradas) y devuelve el resultado como JPG y PDF.

## Funcionalidades

- Procesamiento de SOAT **con monto** (hasta 3 dígitos) o **sin monto**.
- Conversión PDF → imagen con Poppler, ajuste de brillo y saturación.
- Detección automática opcional del identificador (placa) mediante OCR (Tesseract).
- Descarga del resultado en JPG y PDF.

El PDF subido se procesa directamente; no se guarda ninguna plantilla en el repositorio.

## Despliegue en un VPS (Debian/Ubuntu, con sudo)

```bash
git clone <URL-del-repositorio>
cd Editor-Soat
bash deploy.sh
```

El script [deploy.sh](deploy.sh):

1. Instala las dependencias del sistema: **poppler-utils**, **tesseract-ocr** y Python.
2. Crea el entorno virtual e instala las dependencias de Python.
3. Registra un servicio **systemd** (`editor-soat`) que arranca la app con
   **Gunicorn** y la reinicia automáticamente.

La app queda escuchando en `http://<IP-del-VPS>:5000`.

### Opciones

```bash
PORT=8000 bash deploy.sh      # cambiar el puerto (por defecto 5000)
WORKERS=4 bash deploy.sh      # workers de Gunicorn (por defecto 2)
```

### Operación del servicio

```bash
sudo systemctl status editor-soat     # ver estado
sudo journalctl -u editor-soat -f     # ver logs en vivo
sudo systemctl restart editor-soat    # reiniciar (p.ej. tras un git pull)
```

> Nota: la app no incluye autenticación. Exponla solo en una red de confianza o
> detrás de un proxy inverso (p.ej. Nginx) con control de acceso.

## Desarrollo local

```bash
python -m venv venv
# Windows:        .\venv\Scripts\Activate.ps1
# Linux / macOS:  source venv/bin/activate
pip install -r requirements.txt
python recepcion_imagen.py
```

Requiere **Poppler** y, para el OCR, **Tesseract** instalados en el sistema:

- Linux: `sudo apt install poppler-utils tesseract-ocr`
- Windows: descargar Poppler (y apuntar `POPPLER_PATH` a su carpeta `bin`) y
  Tesseract desde https://github.com/UB-Mannheim/tesseract/wiki

## Variables de entorno

| Variable       | Por defecto | Descripción                                              |
|----------------|-------------|---------------------------------------------------------|
| `PORT`         | `5000`      | Puerto del servidor.                                     |
| `HOST`         | `0.0.0.0`   | Interfaz de escucha (solo servidor de desarrollo).      |
| `POPPLER_PATH` | (vacío)     | Ruta al `bin` de Poppler. Si está vacío se usa el PATH.  |

## Estructura del proyecto

```
Editor-Soat/
├── recepcion_imagen.py   # Servidor Flask (rutas, subida y descargas)
├── main.py               # SOATProcessor: lógica de procesamiento de imagen
├── templates/index.html  # Interfaz web
├── assets/               # Imágenes de dígitos por aseguradora + sin-monto.jpg
├── uploads/              # Resultados generados (ignorado por git)
├── deploy.sh             # Script de despliegue (VPS)
└── requirements.txt
```
