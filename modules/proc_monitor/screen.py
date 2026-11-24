"""Process-monitor view listing the busiest processes in a top-style summary."""

import time

import pygame

from core import theme
from core.input import BACK, OPEN
from core.process_manager import ProcessManager
from core.ui.help_view import draw_help_view
from modules.proc_monitor.main import ProcessSampler, ProcessSnapshot


class ProcMonitorScreen:
    """Show the top processes by CPU with PID, memory, and elapsed time."""

    def __init__(self) -> None:
        """Initialize the screen with the first summarized process snapshot."""
        self.show_help = False
        self.sampler = ProcessSampler()
        self.processes: tuple[ProcessSnapshot, ...] = self.sampler.snapshot()
        self.last_refresh = time.monotonic()

    def handle(self, action, processes: ProcessManager) -> bool:
        """Toggle help with A or leave the monitor with B."""
        del processes
        if action == BACK:
            return True
        if action == OPEN:
            self.show_help = not self.show_help
        return False

    def sync(self, processes: ProcessManager) -> None:
        """Refresh the CPU snapshot once per second instead of every frame."""
        del processes
        now = time.monotonic()
        if now - self.last_refresh < 1.0:
            return
        self.last_refresh = now
        self.processes = self.sampler.snapshot()

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
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
        if self.show_help:
            draw_help_view(
                surface,
                body_font,
                body_font,
                small_font,
                "AYUDA PROCESOS",
                (
                    (
                        "PROCESOS ACTIVOS",
                        (
                            "Top por CPU; PID, %CPU, %MEM y tiempo transcurrido.",
                            "Refresca cada segundo; no lanza procesos.",
                        ),
                    ),
                    ("CONTROLES", ("A alterna esta ayuda; B vuelve al menu.",)),
                ),
            )
            return
        if self.processes:
            surface.blit(
                body_font.render("PID %CPU %MEM HRA", False, theme.MUTED_COLOR), (17, 38)
            )
            y = 50
            for snap in self.processes:
                if y + body_font.get_height() >= 212:
                    break
                line = (
                    f"{snap.name[:7]:<7} {snap.pid:>5} {snap.cpu_percent:3.0f}% "
                    f"{snap.memory_percent:3.0f}% {snap.elapsed[:4]}"
                )
                surface.blit(body_font.render(line, False, theme.TEXT_COLOR), (17, y))
                y += 14
        else:
            surface.blit(
                body_font.render("SIN PROCESOS DISPONIBLES.", False, theme.TEXT_COLOR),
                (17, 50),
            )

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return gamepad guidance for the process list or help page."""
        return [("A AYUDA", 12), ("B MENU", 168)]
