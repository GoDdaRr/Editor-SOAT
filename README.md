# Editor SOAT - Entorno Virtual Python

Este proyecto utiliza un entorno virtual de Python con las siguientes dependencias:

## Dependencias Instaladas

- **OpenCV** (opencv-python): Para procesamiento de imágenes y visión por computadora
- **Pillow**: Para manipulación de imágenes
- **NumPy**: Para operaciones numéricas (dependencia de OpenCV)

## Cómo usar el entorno virtual

### Activar el entorno virtual

En Windows PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```

En Windows Command Prompt:
```cmd
venv\Scripts\activate.bat
```

### Ejecutar el proyecto

Una vez activado el entorno virtual:
```bash
python main.py
```

### Instalar nuevas dependencias

```bash
pip install nombre-del-paquete
```

### Desactivar el entorno virtual

```bash
deactivate
```

## Estructura del proyecto

```
Editor-Soat/
├── venv/                 # Entorno virtual
├── main.py              # Archivo principal
├── requirements.txt     # Dependencias del proyecto
└── README.md           # Este archivo
```

## Verificación

El archivo `main.py` incluye un ejemplo básico que verifica que todas las librerías están funcionando correctamente.
