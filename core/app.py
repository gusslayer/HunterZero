import json
import os
import time
from pathlib import Path

import pygame

from core import theme
from core.config import AppSettings
from core.input import BACK, DOWN, OPEN, QUIT, RUN, UP, action_from_event, initialize_joysticks
from core.logger import configure_logging
from core.menu import MenuController
from core.plugins import PluginCatalog
from core.process_manager import ProcessManager
from core.screen import create_display
from core.state import UIState
from core.system_stats import StatsReader, heartbeat_payload
from core.ui import icons
from core.ui.footer import draw_footer
from core.ui.hud import draw_hud
from core.ui.layout import MenuLayout
from core.ui.nmap_screen import NmapScreen
from core.ui.ping_screen import PingScreen


ROOT = Path(__file__).resolve().parents[1]


class HunterZeroApp:
    """Own the event loop, screen state, and shared diagnostic services."""

    def __init__(self) -> None:
        """Load validated configuration and initialize application controllers."""
        self.logger = configure_logging(ROOT)
        self.settings = AppSettings.load(ROOT / "config" / "settings.json")
        self.catalog = PluginCatalog(ROOT / "modules", self.logger)
        self.menu = MenuController(self.catalog.plugins)
        self.state = UIState(ROOT / "state" / "ui_state.json")
        self.state.load(len(self.menu.plugins))
        self.menu.selected = self.state.selected
        self.processes = ProcessManager(ROOT, self.logger)
        self.stats_reader = StatsReader()
        self.stats = self.stats_reader.read()
        self.last_stats = 0.0
        self.last_heartbeat = 0.0
        self.running = True
        self.tool_screen: PingScreen | NmapScreen | None = None
        self.joysticks = []
        self.surface: pygame.Surface
        self.title_font: pygame.font.Font
        self.body_font: pygame.font.Font
        self.small_font: pygame.font.Font

    def run(self) -> None:
        """Initialize Pygame and keep processing gamepad events until exit."""
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise RuntimeError("HunterZero debe ejecutarse como usuario sin privilegios")
        pygame.init()
        pygame.display.set_caption("HunterZero")
        self.surface = create_display()
        self.joysticks = initialize_joysticks(self.logger)
        self.title_font = theme.load_font(16)
        self.body_font = theme.load_font(13)
        self.small_font = theme.load_font(9)
        clock = pygame.time.Clock()
        self.logger.info("Interfaz iniciada")
        try:
            while self.running:
                self._events()
                self._tick()
                self._draw()
                pygame.display.flip()
                clock.tick(theme.FPS)
        finally:
            self.processes.stop()
            self.state.selected = self.menu.selected
            try:
                self.state.save()
            except OSError:
                self.logger.exception("No se pudo guardar el estado del menú.")
            pygame.quit()

    def _events(self) -> None:
        """Translate gamepad events into menu, editor, and tool-screen actions."""
        for event in pygame.event.get():
            action = action_from_event(event)
            if action is None:
                continue
            if action == QUIT:
                self.running = False
                continue
            if self.menu.active_plugin:
                self._handle_plugin_action(action)
            elif action == BACK:
                self.running = False
            elif action == UP:
                self.menu.move(-1)
            elif action == DOWN:
                self.menu.move(1)
            elif action in (OPEN, RUN):
                self._open_selected_plugin()

    def _open_selected_plugin(self) -> None:
        """Open selected module details without running a command implicitly."""
        plugin = self.menu.open()
        if plugin and plugin.identifier == "ping":
            self.tool_screen = PingScreen()
        elif plugin and plugin.identifier == "nmap":
            self.tool_screen = NmapScreen()

    def _handle_plugin_action(self, action) -> None:
        """Route actions to the active tool or return to the module list."""
        if self.tool_screen:
            if self.tool_screen.handle(action, self.processes):
                self.menu.back()
                self.tool_screen = None
            return
        if action == BACK:
            self.menu.back()

    def _tick(self) -> None:
        """Refresh cached telemetry, child-process state, and app heartbeat."""
        now = time.monotonic()
        if now - self.last_stats >= self.settings.stats_interval_seconds:
            self.stats = self.stats_reader.read()
            self.last_stats = now
        self.processes.update()
        if self.tool_screen:
            self.tool_screen.sync(self.processes)
        if now - self.last_heartbeat >= self.settings.heartbeat_interval_seconds:
            try:
                self._write_heartbeat()
                self.last_heartbeat = now
            except OSError:
                self.logger.exception("No se pudo actualizar el heartbeat de la app.")

    def _write_heartbeat(self) -> None:
        """Atomically replace the application's health file with its latest state."""
        heartbeat_path = ROOT / "state" / "heartbeats" / "app.json"
        heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = heartbeat_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(heartbeat_payload()), encoding="utf-8")
        temporary_path.replace(heartbeat_path)

    def _draw(self) -> None:
        """Paint the shared HUD and whichever menu or tool screen is active."""
        self.surface.fill(theme.BLACK)
        draw_hud(self.surface, self.small_font, self.stats)
        if self.tool_screen:
            self.tool_screen.draw(
                self.surface,
                self.title_font,
                self.body_font,
                self.small_font,
                self.processes,
            )
        elif self.menu.active_plugin:
            self._draw_details()
        else:
            self._draw_menu()
        hints = self.tool_screen.footer_hints() if self.tool_screen else None
        draw_footer(self.surface, self.small_font, hints)

    def _draw_menu(self) -> None:
        """Render the scrollable list of module folders."""
        layout = MenuLayout(pygame.Rect(30, 70, 580, 340), 48, 4)
        for index, plugin in enumerate(self.menu.plugins):
            row = layout.row_rect(index)
            selected = index == self.menu.selected
            background = theme.ORANGE if selected else theme.BLACK
            foreground = theme.BLACK if selected else theme.ORANGE
            pygame.draw.rect(self.surface, background, row, border_radius=5)
            icons.draw_icon(self.surface, plugin.icon, pygame.Rect(row.x + 14, row.y + 7, 34, 34), foreground)
            label = self.body_font.render(plugin.name, True, foreground)
            self.surface.blit(label, (row.x + 75, row.y + 15))
            arrow = self.title_font.render(">", True, foreground)
            self.surface.blit(arrow, (row.right - 32, row.y + 13))
        if self.catalog.errors:
            self._draw_text("AVISO: revisa logs/app.log", 30, 412, self.small_font, theme.AMBER)
        if self.processes.message:
            self._draw_text(self.processes.message, 30, 395, self.small_font, theme.AMBER)

    def _draw_details(self) -> None:
        """Explain whether a selected module is implemented and how to continue."""
        plugin = self.menu.active_plugin
        if plugin is None:
            return
        self._draw_text(plugin.name, 38, 90, self.title_font, theme.ORANGE)
        if plugin.identifier == "system_monitor":
            details = (
                f"CPU: {self.stats.cpu_percent}%  RAM: {self.stats.memory_percent}%",
                f"Temperatura: {self.stats.temperature_c if self.stats.temperature_c is not None else '--'} C",
                f"Wi-Fi: {'conectado' if self.stats.wifi_connected else 'desconectado'}",
                f"Batería: {self.stats.battery_percent if self.stats.battery_percent is not None else '--'}%",
            )
            for index, detail in enumerate(details):
                self._draw_text(detail, 38, 150 + index * 42, self.small_font, theme.WHITE)
        else:
            self._draw_wrapped_text(plugin.description, 38, 150, 560, self.small_font, theme.WHITE)
            self._draw_text("Esta función aún no está implementada.", 38, 275, self.small_font, theme.AMBER)
        self._draw_text("B: volver", 38, 345, self.small_font, theme.ORANGE)

    def _draw_text(self, text: str, x: int, y: int, font: pygame.font.Font, color) -> None:
        """Draw one string at an exact pixel coordinate."""
        self.surface.blit(font.render(text, True, color), (x, y))

    def _draw_wrapped_text(
        self,
        text: str,
        x: int,
        y: int,
        max_width: int,
        font: pygame.font.Font,
        color,
    ) -> None:
        """Wrap module descriptions to the available display width."""
        lines = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        for line_index, line in enumerate(lines):
            self._draw_text(line, x, y + line_index * (font.get_linesize() + 4), font, color)


def run() -> None:
    """Configure logging and report uncaught application startup/runtime errors."""
    root = Path(__file__).resolve().parents[1]
    logger = configure_logging(root)
    try:
        HunterZeroApp().run()
    except (pygame.error, OSError, RuntimeError, ValueError) as error:
        logger.exception("La aplicación terminó por un error: %s", error)
        raise
