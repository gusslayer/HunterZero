from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from core.ui.layout import MenuItem


@dataclass(frozen=True)
class Plugin:
    identifier: str
    name: str
    description: str
    icon: str
    path: Path
    screen_path: Path

    def menu_item(self) -> MenuItem:
        """Create a reusable menu label/icon pair for this plugin."""
        return MenuItem(self.name, self.icon)


class PluginCatalog:
    def __init__(self, modules_dir: Path, logger) -> None:
        """Discover module manifests and retain validation errors for logging."""
        self.plugins: list[Plugin] = []
        self.errors: list[str] = []
        self._load(modules_dir, logger)

    def _load(self, modules_dir: Path, logger) -> None:
        """Load valid modules and report invalid manifests."""
        if not modules_dir.exists():
            self.errors.append(f"No existe la carpeta de módulos: {modules_dir}")
            return
        for manifest_path in sorted(modules_dir.glob("*/manifest.yaml")):
            try:
                plugin = self._read_manifest(manifest_path)
                self.plugins.append(plugin)
            except (OSError, yaml.YAMLError, ValueError, TypeError) as error:
                message = f"{manifest_path.parent.name}: {error}"
                self.errors.append(message)
                logger.error("Módulo omitido (%s)", message)
        identifiers = [plugin.identifier for plugin in self.plugins]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Hay identificadores de módulo duplicados")

    @staticmethod
    def _read_manifest(path: Path) -> Plugin:
        """Parse and validate one module manifest and its in-module screen path."""
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("el manifiesto debe ser un objeto YAML")
        identifier = data.get("id")
        name = data.get("name")
        description = data.get("description")
        icon = data.get("icon")
        screen = data.get("screen")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (identifier, name, description, icon, screen)
        ):
            raise ValueError("faltan id, name, description, icon o screen")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", identifier) or screen != "screen.py":
            raise ValueError("id o screen inválido")
        if icon not in {
            "activity", "battery-charging", "bell", "chart",
            "chart-no-axes-combined", "code", "code-xml", "cpu",
            "crosshair", "database", "download", "eye", "folder",
            "gauge", "hard-drive", "lock", "map-pin", "memory-stick",
            "network", "play", "power", "radar", "radio", "rotate-cw",
            "scan-line", "search", "server", "settings", "shield-check",
            "system", "terminal", "upload", "wifi",
        }:
            raise ValueError(f"icono no admitido: {icon}")
        module_dir = path.parent.resolve()
        if identifier != module_dir.name:
            raise ValueError("el id debe coincidir con el nombre de la carpeta")
        screen_path = (module_dir / screen).resolve()
        if screen_path.parent != module_dir or not screen_path.is_file():
            raise ValueError("screen debe ser screen.py dentro del módulo")
        return Plugin(identifier, name, description, icon, module_dir, screen_path)
