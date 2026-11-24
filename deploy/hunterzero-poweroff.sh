#!/usr/bin/env bash
# Apagado físico de la GPi Case 2W con libgpiod (sin RPi.GPIO, heredado).
# La placa mantiene alimentado el circuito por GPIO 27 y el botón de encendido
# baja GPIO 26; en ese flanco descendente se programa un apagado limpio.
# Se instala como /usr/local/bin/hunterzero-poweroff y lo ejecuta root.
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi
set -euo pipefail

GPIO_CHIP="${HUNTERZERO_GPIO_CHIP:-gpiochip0}"
POWER_BUTTON_LINE="${HUNTERZERO_POWER_BUTTON_LINE:-26}"
POWER_ENABLE_LINE="${HUNTERZERO_POWER_ENABLE_LINE:-27}"
CONSUMER="hunterzero-poweroff"
SHUTDOWN_BIN="${HUNTERZERO_SHUTDOWN_BIN:-/usr/sbin/shutdown}"

for tool in gpioset gpiomon; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Falta $tool; instala el paquete gpiod." >&2
        exit 1
    fi
done

if [[ "$GPIO_CHIP" == /* ]]; then
    chip_device="$GPIO_CHIP"
else
    chip_device="/dev/$GPIO_CHIP"
fi
if [[ ! -e "$chip_device" ]]; then
    echo "No existe $chip_device; no se puede vigilar el botón de encendido." >&2
    exit 1
fi
if [[ ! -x "$SHUTDOWN_BIN" ]]; then
    echo "No existe $SHUTDOWN_BIN; no se puede apagar el equipo." >&2
    exit 1
fi

echo "Manteniendo GPIO $POWER_ENABLE_LINE en alto y esperando GPIO $POWER_BUTTON_LINE..."

# gpioset no se cierra solo: mientras viva, mantiene el nivel alto. Si muere,
# el wait -n lo detecta y systemd reinicia el servicio.
gpioset -c "$GPIO_CHIP" -C "$CONSUMER" "$POWER_ENABLE_LINE=1" &
enable_pid=$!
gpiomon -c "$GPIO_CHIP" -C "$CONSUMER" -e falling -b pull-up -p 100ms -n 1 \
    "$POWER_BUTTON_LINE" &
monitor_pid=$!

cleanup() {
    kill "$enable_pid" "$monitor_pid" 2>/dev/null || true
    wait "$enable_pid" "$monitor_pid" 2>/dev/null || true
}
on_signal() {
    cleanup
    exit 0
}
trap cleanup EXIT
trap on_signal INT TERM

set +e
wait -n -p finished_pid "$enable_pid" "$monitor_pid"
finished_status=$?
set -e

if [[ "$finished_pid" != "$monitor_pid" || "$finished_status" -ne 0 ]]; then
    echo "Falló la vigilancia GPIO (proceso $finished_pid, código $finished_status)." >&2
    exit 1
fi

echo "Botón de encendido pulsado: apagando el equipo."
sync
"$SHUTDOWN_BIN" -h now
