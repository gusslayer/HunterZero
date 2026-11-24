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
from core.ui import icons
from core.ui.footer import draw_footer
from core.ui.hud import draw_hud
from core.ui.layout import MenuLayout
from core.ui.update_screen import UpdateScreen
from modules.nmap.screen import NmapScreen
from modules.ping.screen import PingScreen
from modules.proc_monitor.screen import ProcMonitorScreen
from modules.system_monitor.screen import SystemMonitorScreen


ROOT = Path(__file__).resolve().parents[1]

# En el menú principal B no cierra la interfaz: al soltar SDL/KMS el framebuffer
# queda en blanco y el servicio no se reinicia solo. START/A abren las opciones.
MENU_FOOTER_HINTS = [
    ("D-PAD MOVER", 24),
    ("A ABRIR", 190),
    ("START ABRIR", 350),
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
            "ping": PingScreen,
            "nmap": NmapScreen,
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
            PingScreen | NmapScreen | SystemMonitorScreen | ProcMonitorScreen | UpdateScreen | None
        ) = None
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
        _hide_mouse_cursor()
        self.joysticks = initialize_joysticks(self.logger)
        # Press Start 2P es monoespacio: 24/18/14 px caben en 640x480 sin
        # recortes y son legibles en la pantalla DPI de 3,5" de la GPi.
        self.title_font = theme.load_font(24)
        self.body_font = theme.load_font(18)
        self.small_font = theme.load_font(14)
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
        """Return to the module list from any screen without stopping the app."""
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
        self.surface.fill(theme.BLACK)
        draw_hud(self.surface, self.small_font, self.stats)
        if self.tool_screen:
            self.tool_screen.draw(
                self.surface,
                self.title_font,
                self.body_font,
                self.small_font,
                self.processes,
                self.stats,
            )
        elif self.menu.active_plugin:
            self._draw_text(
                "ERROR: PANTALLA DEL MODULO NO DISPONIBLE",
                30,
                190,
                self.small_font,
                theme.AMBER,
            )
        else:
            self._draw_menu()
        hints = self.tool_screen.footer_hints() if self.tool_screen else MENU_FOOTER_HINTS
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
            self._draw_text(self.processes.message[:48], 30, 395, self.small_font, theme.AMBER)

    def _draw_text(self, text: str, x: int, y: int, font: pygame.font.Font, color) -> None:
        """Draw one string at an exact pixel coordinate."""
        self.surface.blit(font.render(text, True, color), (x, y))


def run() -> None:
    """Configure logging and report uncaught application startup/runtime errors."""
    root = Path(__file__).resolve().parents[1]
    logger = configure_logging(root)
    try:
        HunterZeroApp().run()
    except (pygame.error, OSError, RuntimeError, ValueError) as error:
        logger.exception("La aplicación terminó por un error: %s", error)
        raise
