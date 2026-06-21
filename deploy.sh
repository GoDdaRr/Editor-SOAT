#!/usr/bin/env bash
#
# Despliegue de Editor SOAT en un VPS Debian/Ubuntu.
#
# Uso (tras clonar el repositorio):
#   cd Editor-Soat
#   bash deploy.sh
#
# Instala las dependencias del sistema (Poppler, Tesseract), crea el entorno
# virtual de Python, instala las dependencias y registra un servicio systemd
# que arranca la app con Gunicorn y la reinicia automáticamente.
#
# Variables opcionales:
#   PORT=8000 bash deploy.sh      -> cambiar el puerto (por defecto 5000)
#   WORKERS=4 bash deploy.sh      -> número de workers de Gunicorn (por defecto 2)
#
set -euo pipefail

APP_NAME="editor-soat"
APP_MODULE="recepcion_imagen:app"
PORT="${PORT:-5000}"
WORKERS="${WORKERS:-2}"
TIMEOUT="${TIMEOUT:-120}"

# Directorio del proyecto (donde vive este script).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Usuario que ejecutará el servicio (el que invocó el script, nunca root).
RUN_USER="${SUDO_USER:-$(whoami)}"

echo "[i] Proyecto:         $PROJECT_DIR"
echo "[i] Usuario servicio: $RUN_USER"
echo "[i] Puerto:           $PORT"
echo "[i] Workers Gunicorn: $WORKERS"

# 1. Dependencias del sistema -------------------------------------------------
echo "[>] Instalando dependencias del sistema (Poppler, Tesseract, Python)..."
sudo apt-get update
sudo apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    python3 python3-venv python3-pip

# 2. Entorno virtual + dependencias de Python ---------------------------------
echo "[>] Creando entorno virtual e instalando dependencias de Python..."
sudo -u "$RUN_USER" python3 -m venv "$PROJECT_DIR/venv"
sudo -u "$RUN_USER" "$PROJECT_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$RUN_USER" "$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# 3. Carpeta de resultados ----------------------------------------------------
sudo -u "$RUN_USER" mkdir -p "$PROJECT_DIR/uploads"

# 4. Servicio systemd ---------------------------------------------------------
echo "[>] Registrando servicio systemd ($APP_NAME)..."
sudo tee "/etc/systemd/system/$APP_NAME.service" > /dev/null <<EOF
[Unit]
Description=Editor SOAT (Flask + Gunicorn)
After=network.target

[Service]
User=$RUN_USER
WorkingDirectory=$PROJECT_DIR
Environment=PORT=$PORT
ExecStart=$PROJECT_DIR/venv/bin/gunicorn -w $WORKERS --timeout $TIMEOUT -b 0.0.0.0:$PORT $APP_MODULE
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 5. Arrancar el servicio -----------------------------------------------------
sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl restart "$APP_NAME"

echo ""
echo "[+] Despliegue completado."
echo "[+] Estado:  sudo systemctl status $APP_NAME"
echo "[+] Logs:    sudo journalctl -u $APP_NAME -f"
echo "[+] URL:     http://<IP-del-VPS>:$PORT"
