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
    entry_point: Path
    timeout_seconds: int

    def menu_item(self) -> MenuItem:
        return MenuItem(self.name, self.icon)


class PluginCatalog:
    def __init__(self, modules_dir: Path, logger) -> None:
        self.plugins: list[Plugin] = []
        self.errors: list[str] = []
        self._load(modules_dir, logger)

    def _load(self, modules_dir: Path, logger) -> None:
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
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("el manifiesto debe ser un objeto YAML")
        identifier = data.get("id")
        name = data.get("name")
        description = data.get("description")
        icon = data.get("icon")
        entry = data.get("entry_point", "main.py")
        timeout = data.get("timeout_seconds", 30)
        if not all(isinstance(value, str) and value.strip() for value in (identifier, name, description, icon, entry)):
            raise ValueError("faltan id, name, description, icon o entry_point")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", identifier) or entry != "main.py":
            raise ValueError("id o entry_point inválido")
        if icon not in {"network", "system", "folder", "code", "chart", "terminal"}:
            raise ValueError(f"icono no admitido: {icon}")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 3600:
            raise ValueError("timeout_seconds debe estar entre 1 y 3600")
        module_dir = path.parent.resolve()
        if identifier != module_dir.name:
            raise ValueError("el id debe coincidir con el nombre de la carpeta")
        entry_path = (module_dir / entry).resolve()
        if entry_path.parent != module_dir or not entry_path.is_file():
            raise ValueError("entry_point debe ser main.py dentro del módulo")
        return Plugin(identifier, name, description, icon, module_dir, entry_path, timeout)
