"""Process-monitor view listing the busiest processes in a top-style summary."""

import time

import pygame

from core import theme
from core.input import BACK, DOWN, OPEN, UP
from core.process_manager import ProcessManager
from core.ui.help_view import draw_help_view
from core.ui.scroll import ScrollState
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_scroll_indicator, plain_text
from modules.proc_monitor.main import ProcessSampler, ProcessSnapshot


LIST_TOP = 48
LIST_BOTTOM = 208
ROW_HEIGHT = 15
LIST_CAPACITY = (LIST_BOTTOM - LIST_TOP) // ROW_HEIGHT


class ProcMonitorScreen:
    """Show the top processes by CPU with PID, memory, and elapsed time."""

    def __init__(self) -> None:
        """Initialize the screen with the first summarized process snapshot."""
        self.show_help = False
        self.help_scroll = ScrollState()
        self.sampler = ProcessSampler()
        self.processes: tuple[ProcessSnapshot, ...] = self.sampler.snapshot()
        self.list_view = ScrollState(capacity=LIST_CAPACITY)
        self.list_view.update(len(self.processes))
        self.last_refresh = time.monotonic()

    def handle(self, action, processes: ProcessManager) -> bool:
        """Scroll the list with D-pad, toggle help with A, or leave with B."""
        del processes
        if self.show_help:
            if action == OPEN:
                self.show_help = False
            elif action == BACK:
                return True
            elif action == UP:
                self.help_scroll.move(-1)
            elif action == DOWN:
                self.help_scroll.move(1)
            return False
        if action == BACK:
            return True
        if action == OPEN:
            self.show_help = True
        elif action == UP:
            self.list_view.move(-1)
        elif action == DOWN:
            self.list_view.move(1)
        return False

    def sync(self, processes: ProcessManager) -> None:
        """Refresh the CPU snapshot once per second instead of every frame."""
        del processes
        now = time.monotonic()
        if now - self.last_refresh < 1.0:
            return
        self.last_refresh = now
        self.processes = self.sampler.snapshot()
        self.list_view.update(len(self.processes))

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
        del title_font
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
        if self.show_help:
            total, capacity = draw_help_view(
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
                self.help_scroll.offset,
            )
            self.help_scroll.update(total, capacity)
            return
        if self.processes:
            surface.blit(
                render_cached(body_font, "PROC   PID  %CPU %MEM HRA", theme.MUTED_COLOR), (16, 34)
            )
            for position, index in enumerate(range(self.list_view.first, self.list_view.last)):
                snap = self.processes[index]
                y = LIST_TOP + position * ROW_HEIGHT
                line = (
                    f"{snap.name[:7]:<7} {snap.pid:>5} {snap.cpu_percent:3.0f}% "
                    f"{snap.memory_percent:3.0f}% {snap.elapsed[:4]}"
                )
                surface.blit(render_cached(body_font, plain_text(line), theme.TEXT_COLOR), (16, y))
            draw_scroll_indicator(
                surface,
                pygame.Rect(12, LIST_TOP, 296, LIST_BOTTOM - LIST_TOP),
                self.list_view.has_above,
                self.list_view.has_below,
                theme.ACCENT_COLOR,
            )
        else:
            surface.blit(
                render_cached(body_font, "SIN PROCESOS DISPONIBLES.", theme.TEXT_COLOR), (16, 48)
            )

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return gamepad guidance for the process list or help page."""
        if self.show_help:
            return [("ARR/ABA TEXTO", 8), ("A AYUDA", 168), ("B MENU", 240)]
        return [("ARR/ABA LISTA", 8), ("A AYUDA", 150), ("B MENU", 240)]
