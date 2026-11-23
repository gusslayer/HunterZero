#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Ejecuta este instalador con sudo." >&2
    exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="${SUDO_USER:-}"
if [[ -z "$APP_USER" || "$APP_USER" == "root" ]]; then
    echo "Ejecuta el script desde la cuenta de usuario: sudo bash deploy/install.sh" >&2
    exit 1
fi
if ! id "$APP_USER" >/dev/null 2>&1; then
    echo "No existe el usuario $APP_USER." >&2
    exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git python3 python3-venv python3-pygame python3-yaml \
    iputils-ping nmap

python3 -m venv --system-site-packages "$APP_DIR/.venv"
usermod -aG input,video "$APP_USER"
install -d -o "$APP_USER" \
    "$APP_DIR/logs" "$APP_DIR/state/heartbeats" \
    "$APP_DIR/data/scans" "$APP_DIR/data/captures" \
    "$APP_DIR/data/reports" "$APP_DIR/data/targets"

service_tmp="$(mktemp)"
sed -e "s|@APP_USER@|$APP_USER|g" -e "s|@APP_DIR@|$APP_DIR|g" \
    "$APP_DIR/deploy/hunterzero.service" > "$service_tmp"
install -m 0644 "$service_tmp" /etc/systemd/system/hunterzero.service
rm -f "$service_tmp"
systemctl daemon-reload

echo "Instalación lista. Cierra y abre sesión para aplicar los grupos input/video."
echo "Prueba la interfaz y luego ejecuta: sudo systemctl enable --now hunterzero.service"
