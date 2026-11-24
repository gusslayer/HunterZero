"""Independent system-monitor view using shared layout and help components."""

# Lee métricas locales preparadas por core; no ejecuta procesos externos.
import time

import pygame

from core import theme
from core.input import BACK, OPEN
from core.process_manager import ProcessManager
from core.system_stats import SystemStats, disk_usage_percent
from core.ui.help_view import draw_help_view
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_frame, plain_text


class SystemMonitorScreen:
    """Display local telemetry without launching external commands."""

    def __init__(self) -> None:
        """Start the monitor on its dashboard with its reusable help closed."""
        self.show_help = False
        self.disk_percent = disk_usage_percent(theme.ROOT)
        self.last_disk_refresh = time.monotonic()

    def handle(self, action, processes: ProcessManager) -> bool:
        """Toggle help with A or leave the monitor with B."""
        del processes
        if action == BACK:
            return True
        if action == OPEN:
            self.show_help = not self.show_help
        return False

    def sync(self, processes: ProcessManager) -> None:
        """Refresh the disk reading every two seconds instead of every frame."""
        del processes
        now = time.monotonic()
        if now - self.last_disk_refresh < 2.0:
            return
        self.last_disk_refresh = now
        self.disk_percent = disk_usage_percent(theme.ROOT)

    def draw(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        processes: ProcessManager,
        stats: SystemStats,
    ) -> None:
        """Render the local system metrics or the shared gamepad help view."""
        del processes
        if self.show_help:
            draw_help_view(
                surface,
                title_font,
                body_font,
                small_font,
                "AYUDA SISTEMA",
                (
                    (
                        "LECTURAS LOCALES",
                        (
                            "CPU, RAM, temperatura, IP, SSID, Wi-Fi, bateria, disco y hora.",
                            "Temperatura y bateria dependen de lo que exponga el sistema.",
                        ),
                    ),
                    ("CONTROLES", ("A alterna esta ayuda; B vuelve al menu.",)),
                ),
            )
            return
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
        draw_frame(surface, pygame.Rect(10, 32, 300, 136), theme.GRID_COLOR, theme.PANEL_COLOR)
        temperature = f"{stats.temperature_c} C" if stats.temperature_c is not None else "N/D"
        battery = f"{stats.battery_percent}%" if stats.battery_percent is not None else "N/D"
        values = (
            f"CPU: {stats.cpu_percent}%",
            f"RAM: {stats.memory_percent}%",
            f"DISCO: {self.disk_percent}%",
            f"TEMP: {temperature}",
            f"IP: {stats.local_ip}",
            f"SSID: {stats.ssid or 'N/D'}",
            f"WIFI: {'CONECTADO' if stats.wifi_connected else 'NO DISPONIBLE'}",
            f"BATERIA: {battery}",
            f"HORA: {stats.clock}",
        )
        for index, value in enumerate(values):
            color = theme.ACCENT_COLOR if index in (0, 1, 2) else theme.TEXT_COLOR
            surface.blit(
                render_cached(body_font, plain_text(value)[:34], color),
                (18, 38 + index * 15),
            )

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return gamepad guidance for the monitor dashboard or help page."""
        if self.show_help:
            return [("A METRICAS", 12), ("B MENU", 168)]
        return [("A AYUDA", 12), ("B MENU", 168)]
