from core.plugins import Plugin


class MenuController:
    def __init__(self, plugins: list[Plugin]) -> None:
        """Create a menu controller for the registered module list."""
        self.plugins = plugins
        self.selected = 0
        self.active_plugin: Plugin | None = None

    def move(self, offset: int) -> None:
        """Move the selection while the module list is visible."""
        if self.active_plugin or not self.plugins:
            return
        self.selected = (self.selected + offset) % len(self.plugins)

    def open(self) -> Plugin | None:
        """Mark and return the selected plugin, if any."""
        if self.active_plugin:
            return self.active_plugin
        if self.plugins:
            self.active_plugin = self.plugins[self.selected]
            return self.active_plugin
        return None

    def back(self) -> bool:
        """Close the active plugin and report whether navigation succeeded."""
        if self.active_plugin:
            self.active_plugin = None
            return True
        return False
