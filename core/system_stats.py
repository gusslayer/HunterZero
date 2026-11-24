import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


NETWORK_REFRESH_SECONDS = 10.0


@dataclass(frozen=True)
class SystemStats:
    cpu_percent: int
    memory_percent: int
    temperature_c: int | None
    battery_percent: int | None
    clock: str
    wifi_connected: bool
    local_ip: str
    ssid: str | None


def local_ip_address() -> str:
    """Return the address of the interface used for outbound traffic."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # UDP connect only selects a route; it sends no packets.
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "N/D"


def _wireless_interfaces() -> list[str]:
    """List wlan interfaces exposed by sysfs, falling back to the common name."""
    try:
        found = [entry.name for entry in Path("/sys/class/net").iterdir() if entry.name.startswith("wlan")]
    except OSError:
        found = []
    return sorted(found) or ["wlan0"]


def wireless_ssid() -> str | None:
    """Read the connected SSID from iw, wireless-tools, or NetworkManager."""
    for interface in _wireless_interfaces():
        commands = (
            ["iw", "dev", interface, "link"],
            ["iwgetid", "-r"],
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
        )
        for command in commands:
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=1, check=False
                )
            except (OSError, subprocess.SubprocessError):
                continue
            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if command[0] == "iw":
                    # `iw dev ... link` imprime BSS, señal, etc. Solo SSID identifica
                    # la red conectada; aceptar cualquier línea devolvía el BSS.
                    if not line.startswith("SSID:"):
                        continue
                    candidate = line.split(":", 1)[1].strip()
                elif command[0] == "iwgetid":
                    candidate = line.rsplit(":", 1)[1].strip() if ":" in line else line
                else:
                    active, separator, ssid = line.partition(":")
                    candidate = ssid.strip() if separator and active == "yes" else ""
                if candidate:
                    return candidate
    return None


def disk_usage_percent(path: Path) -> int:
    """Return the used-percent of the filesystem containing path."""
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return 0
    if usage.total <= 0:
        return 0
    return max(0, min(100, round(100 * usage.used / usage.total)))


class StatsReader:
    def __init__(self) -> None:
        """Initialize CPU counters and the cached network identity."""
        self._previous_cpu: tuple[int, int] | None = None
        self._network_cache: tuple[str, str | None] | None = None
        self._network_read_at = 0.0

    def read(self) -> SystemStats:
        """Read the current HUD metrics from procfs, sysfs, and the network."""
        now = time.monotonic()
        if self._network_cache is None or now - self._network_read_at >= NETWORK_REFRESH_SECONDS:
            previous = self._network_cache
            self._network_cache = (local_ip_address(), wireless_ssid())
            if previous is not None and self._network_cache == previous:
                # Sin cambios: el valor ya es el mismo, así que espera más
                # tiempo antes de repetir el sondeo de subprocesos.
                self._network_read_at = now + NETWORK_REFRESH_SECONDS * 3
            else:
                self._network_read_at = now
        local_ip, ssid = self._network_cache
        return SystemStats(
            cpu_percent=self._cpu_percent(),
            memory_percent=self._memory_percent(),
            temperature_c=self._temperature(),
            battery_percent=self._battery(),
            clock=datetime.now().strftime("%H:%M"),
            wifi_connected=self._wifi_connected(),
            local_ip=local_ip,
            ssid=ssid,
        )

    @staticmethod
    def _wifi_connected() -> bool:
        """Return whether the wlan0 interface reports an up state."""
        try:
            return Path("/sys/class/net/wlan0/operstate").read_text(
                encoding="ascii"
            ).strip() == "up"
        except OSError:
            return False

    def _cpu_percent(self) -> int:
        """Calculate CPU utilization since the preceding procfs sample."""
        try:
            values = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            total = sum(values)
            previous = self._previous_cpu
            self._previous_cpu = (total, idle)
            if previous is None or total <= previous[0]:
                return 0
            return max(0, min(100, round(100 * (1 - (idle - previous[1]) / (total - previous[0])))))
        except (OSError, ValueError, IndexError):
            return 0

    @staticmethod
    def _memory_percent() -> int:
        """Calculate RAM usage from MemTotal and MemAvailable."""
        try:
            fields = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                key, value = line.split(":", 1)
                fields[key] = int(value.strip().split()[0])
            total = fields["MemTotal"]
            available = fields["MemAvailable"]
            return max(0, min(100, round(100 * (total - available) / total)))
        except (OSError, ValueError, KeyError, IndexError, ZeroDivisionError):
            return 0

    @staticmethod
    def _temperature() -> int | None:
        """Read the first available thermal sensor in degrees Celsius."""
        candidates = [
            Path("/sys/class/thermal/thermal_zone0/temp"),
            Path("/sys/class/hwmon/hwmon0/temp1_input"),
        ]
        for path in candidates:
            try:
                return round(int(path.read_text().strip()) / 1000)
            except (OSError, ValueError):
                continue
        return None

    @staticmethod
    def _battery() -> int | None:
        """Read the first exposed power-supply charge percentage."""
        for capacity in Path("/sys/class/power_supply").glob("*/capacity"):
            try:
                return max(0, min(100, int(capacity.read_text().strip())))
            except (OSError, ValueError):
                continue
        return None


def heartbeat_payload() -> dict[str, object]:
    """Create the JSON-compatible health snapshot for the running application."""
    return {
        "application": "hunterzero",
        "pid": os.getpid(),
        "status": "running",
        "updated_at": time.time(),
    }
