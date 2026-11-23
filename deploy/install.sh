#!/usr/bin/env bash
set -euo pipefail

# El objetivo soportado es Raspberry Pi OS Lite de 32 bits (armhf).
# Comprueba antes de tocar APT para evitar una instalación parcialmente creada.
if [[ "${EUID}" -ne 0 ]]; then
    echo "Ejecuta este instalador con sudo." >&2
    exit 1
fi

if ! command -v dpkg >/dev/null 2>&1; then
    echo "Este instalador requiere una distribución Debian con APT y dpkg." >&2
    exit 1
fi

ARCH="$(dpkg --print-architecture)"
if [[ "$ARCH" != "armhf" && "$ARCH" != "i386" ]]; then
    echo "Arquitectura no admitida: $ARCH. HunterZero requiere un sistema de 32 bits (armhf o i386)." >&2
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
# Paquetes base, Pygame/YAML y herramientas usadas por los módulos activos.
# Todos deben provenir de APT para conservar compatibilidad armhf/ARMv6.
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git sudo udev dbus kmod procps iproute2 kbd \
    python3 python3-venv python3-pip python3-pygame python3-yaml \
    libsdl2-2.0-0 libsdl2-ttf-2.0-0 libsdl2-gfx-1.0-0 \
    fonts-dejavu-core iputils-ping nmap

# Verifica que el binario instalado tenga punteros de 32 bits.
if ! python3 -c 'import struct; raise SystemExit(0 if struct.calcsize("P") == 4 else 1)' >/dev/null 2>&1; then
    echo "Python no está compilado para 32 bits. Instala una versión armhf/i386 compatible." >&2
    exit 1
fi

# Recrea el entorno como el usuario final para que pueda actualizarlo sin root.
rm -rf "$APP_DIR/.venv"
runuser -u "$APP_USER" -- python3 -m venv --system-site-packages "$APP_DIR/.venv"
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
