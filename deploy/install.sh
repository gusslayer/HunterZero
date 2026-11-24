#!/usr/bin/env bash
# Si se invoca con sh/dash, vuelve a ejecutarse con bash: allí no existen EUID ni [[ ]].
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi
set -euo pipefail

# El objetivo soportado es Raspberry Pi OS Lite de 32 bits (armhf).
# Comprueba antes de tocar APT para evitar una instalación parcialmente creada.
if [ "$(id -u)" -ne 0 ]; then
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
# Paquetes base, Pygame/YAML y herramientas compartidas del sistema. Las
# dependencias de los módulos (`iputils-ping`, `nmap`, `dnsutils`) se instalan después con
# deploy/deps.sh, que lee los campos `deps:` de los manifiestos de modules/*/.
# Todos deben provenir de APT para conservar compatibilidad armhf/ARMv6.
# Descartados por no usarse en el código: curl, kbd, procps, iproute2, kmod y
# fonts-dejavu-core (el código lee /proc y /sys directamente y usa las fuentes
# incluidas en assets/fonts). udev y dbus se conservan por la gestión de
# entrada (gamepad/teclado) y la del sistema (logind/systemctl).
# EGL, GLES, GBM, Mesa y libdrm son necesarios en tiempo de ejecución para el
# driver kmsdrm de SDL2; los paquetes -dev no sustituyen al driver de pantalla.
# gpiod aporta gpioset/gpiomon para vigilar el botón físico de encendido.
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates git sudo udev dbus python3 python3-venv python3-pip \
    python3-pygame python3-yaml gpiod \
    libsdl2-2.0-0 libsdl2-ttf-2.0-0 libsdl2-gfx-1.0-0 \
    libegl1 libegl-mesa0 libgles2 libgbm1 libgl1-mesa-dri libdrm2

# Verifica que el binario instalado tenga punteros de 32 bits.
if ! python3 -c 'import struct; raise SystemExit(0 if struct.calcsize("P") == 4 else 1)' >/dev/null 2>&1; then
    echo "Python no está compilado para 32 bits. Instala una versión armhf/i386 compatible." >&2
    exit 1
fi

# Recrea el entorno como el usuario final para que pueda actualizarlo sin root.
rm -rf "$APP_DIR/.venv"
runuser -u "$APP_USER" -- python3 -m venv --system-site-packages "$APP_DIR/.venv"
# /dev/dri/card0 usa el grupo video y /dev/dri/renderD128 el grupo render en Trixie.
USER_GROUPS="input,video"
if getent group render >/dev/null 2>&1; then
    USER_GROUPS="${USER_GROUPS},render"
fi
usermod -aG "$USER_GROUPS" "$APP_USER"
install -d -o "$APP_USER" \
    "$APP_DIR/logs" "$APP_DIR/state/heartbeats"

service_tmp="$(mktemp)"
sed -e "s|@APP_USER@|$APP_USER|g" -e "s|@APP_DIR@|$APP_DIR|g" \
    "$APP_DIR/deploy/hunterzero.service" > "$service_tmp"
install -m 0644 "$service_tmp" /etc/systemd/system/hunterzero.service
rm -f "$service_tmp"

# El apagado físico vive fuera de la app: debe funcionar aunque la interfaz no
# esté arrancada. Se instala como root y usa libgpiod, no RPi.GPIO.
install -m 0755 "$APP_DIR/deploy/hunterzero-poweroff.sh" /usr/local/bin/hunterzero-poweroff
install -m 0644 "$APP_DIR/deploy/hunterzero-poweroff.service" \
    /etc/systemd/system/hunterzero-poweroff.service

systemctl daemon-reload
if [[ -e /dev/gpiochip0 ]]; then
    systemctl enable --now hunterzero-poweroff.service
else
    echo "Aviso: no existe /dev/gpiochip0; no se habilitó el apagado por GPIO." >&2
fi

# Configura la pantalla DPI de la GPi Case 2W. En equipos sin /boot/firmware
# (por ejemplo, una prueba en i386) se omite sin abortar la instalación.
if [[ -d /boot/firmware ]]; then
    bash "$APP_DIR/deploy/display-config.sh"
else
    echo "Aviso: no existe /boot/firmware; se omite la configuración de pantalla GPi." >&2
fi

# Instala en APT los paquetes declarados por los módulos de la copia clonada.
bash "$APP_DIR/deploy/deps.sh"

echo "Instalación lista. Cierra y abre sesión para aplicar los grupos input/video."
echo "Si se instaló la configuración de pantalla, reinicia la Pi: sudo reboot"
echo "El botón físico GPIO 26 apaga la Pi mediante hunterzero-poweroff.service."
echo "Prueba la interfaz y luego ejecuta: sudo systemctl enable --now hunterzero.service"
