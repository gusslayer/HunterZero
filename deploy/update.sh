#!/usr/bin/env bash
set -euo pipefail

# Actualización segura: conserva los cambios locales, exige usuario sin root y reinicia el servicio.
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${EUID}" -eq 0 ]]; then
    echo "Ejecuta la actualización con tu usuario normal, usando sudo solo para systemctl." >&2
    exit 1
fi
git -C "$APP_DIR" pull --ff-only
sudo systemctl restart hunterzero.service
sudo systemctl --no-pager --full status hunterzero.service
