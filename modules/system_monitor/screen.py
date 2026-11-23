"""Independent system-monitor view using shared layout and help components."""

# Lee métricas locales preparadas por core; no ejecuta procesos externos.
import pygame

from core import theme
from core.input import BACK, OPEN
from core.process_manager import ProcessManager
from core.system_stats import SystemStats, disk_usage_percent
from core.ui.help_view import draw_help_view


class SystemMonitorScreen:
    """Display local telemetry without launching external commands."""

    def __init__(self) -> None:
        """Start the monitor on its dashboard with its reusable help closed."""
        self.show_help = False

    def handle(self, action, processes: ProcessManager) -> bool:
        """Toggle help with A or leave the monitor with B."""
        del processes
        if action == BACK:
            return True
        if action == OPEN:
            self.show_help = not self.show_help
        return False

    def sync(self, processes: ProcessManager) -> None:
        """Implement the common screen contract; telemetry is read by the app."""
        del processes

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
                            "CPU, RAM, temperatura, Wi-Fi, bateria, disco y hora.",
                            "Temperatura y bateria dependen de lo que exponga el sistema.",
                        ),
                    ),
                    ("CONTROLES", ("A alterna esta ayuda; B vuelve al menu.",)),
                ),
            )
            return
        pygame.draw.rect(surface, theme.BLACK, (0, 55, theme.WIDTH, 370))
        surface.blit(title_font.render("MONITOR DEL SISTEMA", True, theme.ORANGE), (30, 72))
        temperature = f"{stats.temperature_c} C" if stats.temperature_c is not None else "N/D"
        battery = f"{stats.battery_percent}%" if stats.battery_percent is not None else "N/D"
        values = (
            f"CPU: {stats.cpu_percent}%",
            f"RAM: {stats.memory_percent}%",
            f"DISK: {disk_usage_percent(theme.ROOT)}%",
            f"TEMPERATURA: {temperature}",
            f"WI-FI: {'CONECTADO' if stats.wifi_connected else 'NO DISPONIBLE'}",
            f"BATERIA: {battery}",
            f"HORA: {stats.clock}",
        )
        for index, value in enumerate(values):
            surface.blit(body_font.render(value, True, theme.WHITE), (34, 128 + index * 36))
        surface.blit(small_font.render("A: ayuda    B: volver", True, theme.AMBER), (34, 365))

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return gamepad guidance for the monitor dashboard or help page."""
        if self.show_help:
            return [("A METRICAS", 24), ("B MENU", 335)]
        return [("A AYUDA", 24), ("B MENU", 335)]
