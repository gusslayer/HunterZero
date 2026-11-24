"""Process-monitor view listing the busiest processes in a top-style summary."""

import pygame

from core import theme
from core.input import BACK, OPEN
from core.process_manager import ProcessManager
from core.ui.help_view import draw_help_view
from modules.proc_monitor.main import ProcessSnapshot, snapshot_processes


class ProcMonitorScreen:
    """Show the top processes by CPU with PID, memory, and elapsed time."""

    def __init__(self) -> None:
        """Initialize the screen with the first summarized process snapshot."""
        self.show_help = False
        self.processes: tuple[ProcessSnapshot, ...] = snapshot_processes()

    def handle(self, action, processes: ProcessManager) -> bool:
        """Toggle help with A or leave the monitor with B."""
        del processes
        if action == BACK:
            return True
        if action == OPEN:
            self.show_help = not self.show_help
        return False

    def sync(self, processes: ProcessManager) -> None:
        """Refresh the summarized process snapshot on every app tick."""
        del processes
        self.processes = snapshot_processes()

    def draw(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        processes: ProcessManager,
        stats,
    ) -> None:
        """Render the process list or the shared gamepad help view."""
        del processes
        del stats
        surface.fill(theme.BLACK)
        surface.blit(title_font.render("MONITOR DE PROCESOS", True, theme.ORANGE), (30, 72))
        if self.show_help:
            draw_help_view(
                surface,
                title_font,
                body_font,
                small_font,
                "AYUDA PROCESOS",
                (
                    (
                        "PROCESOS ACTIVOS",
                        (
                            "Top por CPU; PID, %CPU, %MEM y tiempo transcurrido.",
                            "Refresca cada ciclo de la app; no lanza procesos.",
                        ),
                    ),
                    ("CONTROLES", ("A alterna esta ayuda; B vuelve al menu.",)),
                ),
            )
            return
        if self.processes:
            for index, snap in enumerate(self.processes):
                line = (
                    f"{snap.name[:11]:<11} {snap.pid:>5} {snap.cpu_percent:4.0f}% "
                    f"{snap.memory_percent:4.0f}% {snap.elapsed[:6]}"
                )
                surface.blit(body_font.render(line, True, theme.WHITE), (34, 128 + index * 32))
        else:
            surface.blit(
                body_font.render("Sin procesos disponibles.", True, theme.WHITE),
                (34, 128),
            )
        surface.blit(small_font.render("A: ayuda    B: volver", True, theme.AMBER), (34, 365))

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return gamepad guidance for the process list or help page."""
        return [("A AYUDA", 24), ("B MENU", 335)]
