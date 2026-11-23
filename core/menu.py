from core.plugins import Plugin


class MenuController:
    def __init__(self, plugins: list[Plugin]) -> None:
        self.plugins = plugins
        self.selected = 0
        self.active_plugin: Plugin | None = None

    def move(self, offset: int) -> None:
        if self.active_plugin or not self.plugins:
            return
        self.selected = (self.selected + offset) % len(self.plugins)

    def open(self) -> Plugin | None:
        if self.active_plugin:
            return self.active_plugin
        if self.plugins:
            self.active_plugin = self.plugins[self.selected]
            return self.active_plugin
        return None

    def back(self) -> bool:
        if self.active_plugin:
            self.active_plugin = None
            return True
        return False
