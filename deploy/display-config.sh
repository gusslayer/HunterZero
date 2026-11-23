#!/usr/bin/env bash
set -euo pipefail

# Instala la configuración de pantalla DPI de la GPi Case 2W en Raspberry Pi OS Trixie.
# Trixie monta la partición de arranque en /boot/firmware, no en /boot.
if [[ "${EUID}" -ne 0 ]]; then
    echo "Ejecuta este script con sudo: sudo bash deploy/display-config.sh" >&2
    exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_TARGET="/boot/firmware/config.txt"
CONFIG_BACKUP="${CONFIG_TARGET}.hunterzero.bak"

if [[ ! -f "$CONFIG_TARGET" ]]; then
    echo "No existe $CONFIG_TARGET. Este script requiere Raspberry Pi OS Trixie o superior." >&2
    exit 1
fi
if [[ ! -f "$APP_DIR/deploy/config.txt" ]]; then
    echo "Falta $APP_DIR/deploy/config.txt en la copia clonada." >&2
    exit 1
fi

# Conserva el original real aunque el instalador se ejecute más de una vez.
if [[ ! -e "$CONFIG_BACKUP" ]]; then
    cp -a "$CONFIG_TARGET" "$CONFIG_BACKUP"
fi
install -m 0644 "$APP_DIR/deploy/config.txt" "$CONFIG_TARGET"

echo "Configuración de pantalla instalada en $CONFIG_TARGET."
echo "Original conservado en $CONFIG_BACKUP."
echo "Reinicia la Pi para aplicarla: sudo reboot"
