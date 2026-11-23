import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SystemStats:
    cpu_percent: int
    memory_percent: int
    temperature_c: int | None
    battery_percent: int | None
    clock: str
    wifi_connected: bool


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
        """Initialize CPU counters used to calculate usage between samples."""
        self._previous_cpu: tuple[int, int] | None = None

    def read(self) -> SystemStats:
        """Read the current HUD metrics from procfs and sysfs."""
        return SystemStats(
            cpu_percent=self._cpu_percent(),
            memory_percent=self._memory_percent(),
            temperature_c=self._temperature(),
            battery_percent=self._battery(),
            clock=datetime.now().strftime("%H:%M"),
            wifi_connected=self._wifi_connected(),
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
