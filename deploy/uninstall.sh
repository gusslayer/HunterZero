#!/usr/bin/env bash
# Si se invoca con sh/dash, vuelve a ejecutarse con bash: allí no existen EUID ni [[ ]].
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi
set -euo pipefail

echo "=== Desinstalando HunterZero ==="

# 1. Detener y desactivar servicios systemd
echo "Deteniendo servicios del sistema..."
systemctl stop hunterzero.service 2>/dev/null || true
systemctl disable hunterzero.service 2>/dev/null || true
systemctl stop hunterzero-poweroff.service 2>/dev/null || true
systemctl disable hunterzero-poweroff.service 2>/dev/null || true

# 2. Remover los archivos de servicio
echo "Removiendo archivos de servicio..."
rm -f /etc/systemd/system/hunterzero.service
rm -f /etc/systemd/system/hunterzero-poweroff.service

# 3. Remover el binario de apagado físico
echo "Removiendo hunterzero-poweroff..."
rm -f /usr/local/bin/hunterzero-poweroff

# 4. Ir a directorio de la app y remover el entorno virtual y la app
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Directorio de la app: $APP_DIR"

echo "Deteniendo cualquier proceso en ejecución..."
if [ -n "${SUDO_USER:-}" ]; then
    su - "${SUDO_USER}" -c "pkill -f 'python.*main.py' || true" 2>/dev/null || true
fi

# 5. Remover el entorno virtual de Python
echo "Removiendo entorno virtual..."
rm -rf "$APP_DIR/.venv"

# 6. Remover la aplicación en sí
echo "Removiendo directorio de la app..."
rm -rf "$APP_DIR"

# 7. Revertir la configuración de pantalla (config.txt) si hay backup
CONFIG_TARGET="/boot/firmware/config.txt"
CONFIG_BACKUP="${CONFIG_TARGET}.hunterzero.bak"
if [ -f "$CONFIG_BACKUP" ]; then
    echo "Revertiendo configuración de pantalla..."
    cp -a "$CONFIG_BACKUP" "$CONFIG_TARGET"
    # Opcional: remover el backup también
    # rm -f "$CONFIG_BACKUP"
fi

# 8. Desinstalar paquetes APT instalados por el instalador y módulos
echo "Desinstalando paquetes APT..."
DEBIAN_FRONTEND=noninteractive apt-get purge -y \
    python3-pygame \
    python3-yaml \
    gpiod \
    libsdl2-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libsdl2-gfx-1.0-0 \
    libegl1 \
    libegl-mesa0 \
    libgles2 \
    libgbm1 \
    libgl1-mesa-dri \
    libdrm2 \
    bluez \
    libbluetooth-dev \
    ca-certificates git sudo udev dbus \
  2>/dev/null || echo "Algunos paquetes no estaban instalados o fallaron."

# 9. Mensaje final
echo "=== Desinstalación completa ==="
echo "Cierra y abre sesión para aplicar los cambios de grupos."
echo "Si configuraste la pantalla GPi, reinicia la Pi: sudo reboot"