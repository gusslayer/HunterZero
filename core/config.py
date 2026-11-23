import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    stats_interval_seconds: int = 2
    heartbeat_interval_seconds: int = 5

    @classmethod
    def load(cls, path: Path) -> "AppSettings":
        """Load validated optional settings or return the documented defaults."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"No se pudo leer la configuración {path}: {error}") from error
        if not isinstance(data, dict):
            raise RuntimeError("La configuración debe ser un objeto JSON")
        allowed = {
            "stats_interval_seconds",
            "heartbeat_interval_seconds",
        }
        unknown = set(data) - allowed
        if unknown:
            raise RuntimeError(f"Claves de configuración desconocidas: {', '.join(sorted(unknown))}")
        values = {}
        for key in allowed:
            value = data.get(key, getattr(cls(), key))
            if not isinstance(value, int) or isinstance(value, bool):
                raise RuntimeError(f"{key} debe ser un entero")
            minimum = 1
            maximum = 60
            if not minimum <= value <= maximum:
                raise RuntimeError(f"{key} debe estar entre {minimum} y {maximum}")
            values[key] = value
        return cls(**values)
