import json
from pathlib import Path


class UIState:
    def __init__(self, path: Path) -> None:
        """Create a state store for the last selected menu row."""
        self.path = path
        self.selected = 0

    def load(self, item_count: int) -> None:
        """Read and clamp the saved menu selection to the available item count."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("el estado debe ser un objeto JSON")
            selected = data.get("selected", 0)
            if not isinstance(selected, int) or isinstance(selected, bool):
                raise ValueError("'selected' debe ser un entero")
            self.selected = min(max(selected, 0), max(item_count - 1, 0))
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise RuntimeError(f"No se pudo leer el estado de interfaz: {error}") from error

    def save(self) -> None:
        """Atomically persist the selected menu row as JSON."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"selected": self.selected}, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
