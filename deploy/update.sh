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
# Sin TTY, git no muestra progreso salvo que se pida explícitamente; la pantalla
# necesita salida progresiva. Tampoco debe quedarse esperando credenciales.
export GIT_TERMINAL_PROMPT=0
echo "Descargando código con git pull --ff-only..."
git -C "$APP_DIR" -c color.ui=false pull --ff-only --progress
echo "Descarga completada."

# La interfaz se actualiza a sí misma desde el gamepad: sin tty sudo no puede
# pedir contraseña, y reiniciar el servicio aquí mataría la propia interfaz antes
# de que pueda mostrar el resultado. En ese modo solo se descarga el código.
if [[ "${HUNTERZERO_UPDATE_GUI:-0}" == "1" ]]; then
    echo "Código actualizado. Para completar, ejecuta por SSH:"
    echo "  cd ~/HunterZero && sudo bash deploy/update.sh"
    exit 0
fi

# Instala en APT los paquetes nuevos declarados por los módulos tras el pull.
sudo bash "$APP_DIR/deploy/deps.sh"

# El apagado físico se introdujo en una revisión posterior al instalador inicial:
# sin esto, un update sustituye el overlay gpio-shutdown pero deja la Pi sin
# ningún watcher del botón. Mantener la unidad aquí evita ese estado.
echo "Instalando el servicio de apagado físico por GPIO..."
sudo install -m 0755 "$APP_DIR/deploy/hunterzero-poweroff.sh" \
    /usr/local/bin/hunterzero-poweroff
sudo install -m 0644 "$APP_DIR/deploy/hunterzero-poweroff.service" \
    /etc/systemd/system/hunterzero-poweroff.service
sudo systemctl daemon-reload
if [[ -e /dev/gpiochip0 ]]; then
    sudo systemctl enable --now hunterzero-poweroff.service
else
    echo "Aviso: no existe /dev/gpiochip0; no se habilitó el apagado por GPIO." >&2
fi

sudo systemctl restart hunterzero.service
sudo systemctl --no-pager --full status hunterzero.service
