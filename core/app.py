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
from core.plugins import Plugin, PluginCatalog
from core.process_manager import ProcessManager
from core.screen import create_display
from core.state import UIState
from core.system_stats import StatsReader, heartbeat_payload
from core.ui.footer import draw_footer
from core.ui.hud import draw_hud
from core.ui.layout import MenuLayout
from core.ui.text_cache import render_cached
from core.ui.update_screen import UpdateScreen
from core.ui.widgets import draw_frame, draw_row, draw_scroll_indicator, plain_text, wrap_text
from modules.bleeding.screen import BleedingScreen
from modules.nmap.screen import NmapScreen
from modules.nslookup.screen import NsLookupScreen
from modules.ping.screen import PingScreen
from modules.proc_monitor.screen import ProcMonitorScreen
from modules.system_monitor.screen import SystemMonitorScreen


ROOT = Path(__file__).resolve().parents[1]

# En el menú principal B no cierra la interfaz: al soltar SDL/KMS el framebuffer
# queda en blanco y el servicio no se reinicia solo. START/A abren las opciones.
MENU_FOOTER_HINTS = [
    ("D-PAD MOVER", 12),
    ("A ABRIR", 116),
    ("START ABRIR", 188),
]


def _hide_mouse_cursor() -> None:
    """Ocultar el cursor de SDL para que en el framebuffer solo se vea la interfaz."""
    pygame.mouse.set_visible(False)


class HunterZeroApp:
    """Own the event loop, screen state, and shared diagnostic services."""

    def __init__(self) -> None:
        """Load validated configuration and initialize application controllers."""
        self.logger = configure_logging(ROOT)
        self.settings = AppSettings.load(ROOT / "config" / "settings.json")
        self.screen_types = {
            "bleeding": BleedingScreen,
            "ping": PingScreen,
            "nmap": NmapScreen,
            "nslookup": NsLookupScreen,
            "system_monitor": SystemMonitorScreen,
            "proc_monitor": ProcMonitorScreen,
            "update": UpdateScreen,
        }
        self.catalog = PluginCatalog(ROOT / "modules", self.logger)
        registered_plugins = []
        for plugin in self.catalog.plugins:
            if plugin.identifier in self.screen_types:
                registered_plugins.append(plugin)
            else:
                message = f"{plugin.identifier}: pantalla no registrada en core/app.py"
                self.catalog.errors.append(message)
                self.logger.error("Módulo omitido (%s)", message)
        self.update_plugin = Plugin(
            identifier="update",
            name="ACTUALIZAR HUNTERZERO",
            description=(
                "Descarga el código con git pull --ff-only; los pasos con sudo "
                "se indican al terminar."
            ),
            icon="rotate-cw",
            path=ROOT,
            screen_path=ROOT / "core" / "ui" / "update_screen.py",
        )
        self.menu = MenuController([*registered_plugins, self.update_plugin])
        self.state = UIState(ROOT / "state" / "ui_state.json")
        self.state.load(len(self.menu.plugins))
        self.menu.selected = self.state.selected
        self.processes = ProcessManager(ROOT, self.logger)
        self.stats_reader = StatsReader()
        self.stats = self.stats_reader.read()
        self.last_stats = 0.0
        self.last_heartbeat = 0.0
        self.running = True
        self.tool_screen: (
            BleedingScreen
            | PingScreen
            | NmapScreen
            | NsLookupScreen
            | SystemMonitorScreen
            | ProcMonitorScreen
            | UpdateScreen
            | None
        ) = None
        self.joysticks = []
        self.surface: pygame.Surface
        self.virtual_screen: pygame.Surface
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
        self.virtual_screen = pygame.Surface((320, 240)).convert()
        _hide_mouse_cursor()
        self.joysticks = initialize_joysticks(self.logger)
        self.title_font = theme.load_font(16)
        # La fuente de tamaño 8 es una sola instancia: body y small comparten.
        self.body_font = theme.load_font(8)
        self.small_font = self.body_font
        # Los botones mantenidos durante el arranque generan eventos al iniciar
        # SDL; se descartan para no entrar en un módulo sin que el usuario pulse.
        pygame.event.clear()
        clock = pygame.time.Clock()
        self.logger.info("Interfaz iniciada")
        try:
            while self.running:
                self._events()
                self._tick()
                self._draw()
                pygame.transform.scale(
                    self.virtual_screen,
                    (theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT),
                    self.surface,
                )
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
                # SDL puede emitir SDL_QUIT al cambiar de VT o consola. No hay
                # ningún control de salida en la GPi: volver al menú, nunca cerrar.
                self.processes.stop()
                self._close_tool_screen()
                continue
            if self.menu.active_plugin:
                self._handle_plugin_action(action)
            elif action == UP:
                self.menu.move(-1)
            elif action == DOWN:
                self.menu.move(1)
            elif action in (OPEN, RUN):
                self._open_selected_plugin()

    def _open_selected_plugin(self) -> None:
        """Create the registered module screen without running a command implicitly."""
        plugin = self.menu.open()
        if plugin is None:
            return
        screen_type = self.screen_types.get(plugin.identifier)
        if screen_type is None:
            self.logger.error(
                "El módulo %s no tiene una pantalla registrada en core/app.py.",
                plugin.identifier,
            )
            self.menu.back()
            return
        self.tool_screen = screen_type()

    def _close_tool_screen(self) -> None:
        """Return to the module list and let screens stop their own background work."""
        screen = self.tool_screen
        closer = getattr(screen, "close", None)
        if callable(closer):
            closer()
        self.menu.back()
        self.tool_screen = None

    def _handle_plugin_action(self, action) -> None:
        """Route actions to the active tool or return to the module list."""
        if self.tool_screen:
            # START dentro de un módulo equivale a A: ejecuta o confirma la
            # acción de la pantalla en lugar de quedarse sin efecto.
            if action == RUN:
                action = OPEN
            if self.tool_screen.handle(action, self.processes):
                self._close_tool_screen()
            return
        if action == BACK:
            self._close_tool_screen()

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
        self.virtual_screen.fill(theme.BG_COLOR)
        draw_hud(self.virtual_screen, self.small_font, self.stats)
        if self.tool_screen:
            self.tool_screen.draw(
                self.virtual_screen,
                self.title_font,
                self.body_font,
                self.small_font,
                self.processes,
                self.stats,
            )
        elif self.menu.active_plugin:
            self._draw_text(
                "ERROR: PANTALLA DEL MODULO NO DISPONIBLE",
                15,
                95,
                self.small_font,
                theme.ACCENT_COLOR,
            )
        else:
            self._draw_menu()
        hints = self.tool_screen.footer_hints() if self.tool_screen else MENU_FOOTER_HINTS
        draw_footer(self.virtual_screen, self.small_font, hints)

    def _draw_menu(self) -> None:
        """Render the module list and the selected module's details without a title band."""
        selected_plugin = self.menu.plugins[self.menu.selected] if self.menu.plugins else None
        draw_frame(
            self.virtual_screen, pygame.Rect(10, 32, 300, 132), theme.GRID_COLOR, theme.BG_COLOR
        )
        layout = MenuLayout(pygame.Rect(13, 35, 294, 126), 19, 2)
        first, last = layout.visible_range(len(self.menu.plugins), self.menu.selected)
        for position, index in enumerate(range(first, last)):
            plugin = self.menu.plugins[index]
            draw_row(
                self.virtual_screen,
                layout.row_rect(position),
                plugin.name,
                "",
                index == self.menu.selected,
                self.body_font,
                plugin.icon,
            )
        draw_scroll_indicator(
            self.virtual_screen,
            layout.bounds,
            first > 0,
            last < len(self.menu.plugins),
            theme.ACCENT_COLOR,
        )

        draw_frame(
            self.virtual_screen, pygame.Rect(10, 168, 300, 41), theme.GRID_COLOR, theme.PANEL_COLOR
        )
        if selected_plugin:
            description = wrap_text(selected_plugin.description, 34)
            visible_lines = description[:2]
            if len(description) > 2 and visible_lines:
                visible_lines[-1] = f"{visible_lines[-1]}.."
            for line_index, line in enumerate(visible_lines):
                color = theme.ACCENT_COLOR if line_index == 0 else theme.TEXT_COLOR
                self._draw_text(line, 16, 171 + line_index * 10, self.small_font, color)
        pygame.draw.line(self.virtual_screen, theme.GRID_COLOR, (15, 190), (305, 190), 1)
        if self.catalog.errors:
            status, color = "AVISO: REVISA LOGS/APP.LOG", theme.ACCENT_COLOR
        elif self.processes.message:
            status, color = self.processes.message[:34], theme.ACCENT_COLOR
        else:
            wifi = "ON" if self.stats.wifi_connected else "OFF"
            status, color = f"IP {self.stats.local_ip}  WIFI {wifi}", theme.MUTED_COLOR
        self._draw_text(plain_text(status)[:34], 16, 195, self.small_font, color)

    def _draw_text(self, text: str, x: int, y: int, font: pygame.font.Font, color) -> None:
        """Draw one string at an exact pixel coordinate."""
        self.virtual_screen.blit(render_cached(font, text, color), (x, y))


def run() -> None:
    """Configure logging and report uncaught application startup/runtime errors."""
    root = Path(__file__).resolve().parents[1]
    logger = configure_logging(root)
    try:
        HunterZeroApp().run()
    except (pygame.error, OSError, RuntimeError, ValueError) as error:
        logger.exception("La aplicación terminó por un error: %s", error)
        raise
