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


ROOT = Path(__file__).resolve().parents[1]


class HunterZeroApp:
    def __init__(self) -> None:
        self.logger = configure_logging(ROOT)
        self.settings = AppSettings.load(ROOT / "config" / "settings.json")
        self.catalog = PluginCatalog(ROOT / "modules", self.logger)
        self.menu = MenuController(self.catalog.plugins)
        self.state = UIState(ROOT / "state" / "ui_state.json")
        self.state.load(len(self.menu.plugins))
        self.menu.selected = self.state.selected
        self.processes = ProcessManager(
            ROOT,
            self.logger,
            self.settings.module_heartbeat_timeout_seconds,
        )
        self.stats_reader = StatsReader()
        self.stats = self.stats_reader.read()
        self.last_stats = 0.0
        self.last_heartbeat = 0.0
        self.running = True
        self.joysticks = []
        self.surface: pygame.Surface
        self.title_font: pygame.font.Font
        self.body_font: pygame.font.Font
        self.small_font: pygame.font.Font

    def run(self) -> None:
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
            self.state.save()
            pygame.quit()

    def _events(self) -> None:
        for event in pygame.event.get():
            action = action_from_event(event)
            if action is None:
                continue
            if action == QUIT:
                self.running = False
            elif action == BACK:
                if not self.menu.back():
                    self.running = False
            elif action == UP:
                self.menu.move(-1)
            elif action == DOWN:
                self.menu.move(1)
            elif action == OPEN:
                if self.menu.active_plugin:
                    self.processes.start(self.menu.active_plugin)
                else:
                    self.menu.open()
            elif action == RUN:
                if self.menu.active_plugin:
                    self.processes.start(self.menu.active_plugin)
                elif self.menu.plugins:
                    self.processes.start(self.menu.plugins[self.menu.selected])

    def _tick(self) -> None:
        now = time.monotonic()
        if now - self.last_stats >= self.settings.stats_interval_seconds:
            self.stats = self.stats_reader.read()
            self.last_stats = now
        self.processes.update()
        if now - self.last_heartbeat >= self.settings.heartbeat_interval_seconds:
            self._write_heartbeat()
            self.last_heartbeat = now

    def _write_heartbeat(self) -> None:
        heartbeat_path = ROOT / "state" / "heartbeats" / "app.json"
        heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = heartbeat_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(heartbeat_payload()), encoding="utf-8")
        temporary_path.replace(heartbeat_path)

    def _draw(self) -> None:
        self.surface.fill(theme.BLACK)
        draw_hud(self.surface, self.small_font, self.stats)
        if self.menu.active_plugin:
            self._draw_details()
        else:
            self._draw_menu()
        draw_footer(self.surface, self.small_font)

    def _draw_menu(self) -> None:
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
        plugin = self.menu.active_plugin
        if plugin is None:
            return
        self._draw_text(plugin.name, 38, 90, self.title_font, theme.ORANGE)
        self._draw_wrapped_text(plugin.description, 38, 150, 560, self.body_font, theme.WHITE)
        self._draw_text("A: ejecutar plantilla segura", 38, 235, self.small_font, theme.ORANGE)
        self._draw_text(self.processes.message, 38, 345, self.small_font, theme.AMBER)
        self._draw_text("Las plantillas no realizan acciones del sistema.", 38, 390, self.small_font, theme.WHITE)

    def _draw_text(self, text: str, x: int, y: int, font: pygame.font.Font, color) -> None:
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
    root = Path(__file__).resolve().parents[1]
    logger = configure_logging(root)
    try:
        HunterZeroApp().run()
    except (pygame.error, OSError, RuntimeError, ValueError) as error:
        logger.exception("La aplicación terminó por un error: %s", error)
        raise
