#!/usr/bin/env bash
# Si se invoca con sh/dash, vuelve a ejecutarse con bash: allí no existen EUID ni [[ ]].
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi
set -euo pipefail

# Actualización segura: conserva los cambios locales, exige usuario sin root y reinicia el servicio.
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "$(id -u)" -eq 0 ]; then
    echo "Ejecuta la actualización con tu usuario normal, usando sudo solo para systemctl." >&2
    exit 1
fi
git -C "$APP_DIR" pull --ff-only

# Instala en APT los paquetes nuevos declarados por los módulos tras el pull.
sudo bash "$APP_DIR/deploy/deps.sh"

sudo systemctl restart hunterzero.service
sudo systemctl --no-pager --full status hunterzero.service
