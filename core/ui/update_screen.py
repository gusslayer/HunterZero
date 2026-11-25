"""Screen that runs the repository update flow from the main menu."""

import time

import pygame

from core import theme
from core.input import BACK, DOWN, OPEN, UP
from core.process_manager import ProcessManager
from core.ui.scroll import ScrollState
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_scroll_indicator, plain_text, wrap_text


RESULT_TOP = 38
RESULT_BOTTOM = 208
RESULT_ROW = 16


class UpdateScreen:
    """Guide the user through running deploy/update.sh with captured output."""

    def __init__(self) -> None:
        """Start the screen on the confirmation phase."""
        self.title = "ACTUALIZAR"
        self.phase = "confirm"
        self.started_at = 0.0
        self.last_sync = 0.0
        self.activity = 0.0
        self.result_view = ScrollState(capacity=(RESULT_BOTTOM - RESULT_TOP) // RESULT_ROW)

    def handle(self, action, processes: ProcessManager) -> bool:
        """Start the update on OPEN, cancel on BACK, and exit when finished."""
        if self.phase == "confirm":
            if action == OPEN:
                if not processes.start_update():
                    self.phase = "result"
                    return False
                self.started_at = time.monotonic()
                self.last_sync = self.started_at
                self.activity = 0.0
                self.phase = "running"
            elif action == BACK:
                return True
            return False
        if self.phase == "running":
            if action == BACK:
                processes.stop()
                self.phase = "result"
            return False
        self.result_view.update(len(self._result_lines(processes)))
        if action == UP:
            self.result_view.move(-1)
            return False
        if action == DOWN:
            self.result_view.move(1)
            return False
        return True

    def sync(self, processes: ProcessManager) -> None:
        """Advance the activity marker and move to results once git finishes."""
        now = time.monotonic()
        if self.phase == "running":
            self.activity += max(0.0, now - self.last_sync)
        self.last_sync = now
        if self.phase == "running" and processes.running is None:
            self.phase = "result"

    def draw(
        self,
        surface: pygame.Surface,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
        processes: ProcessManager,
        stats,
    ) -> None:
        """Render the confirmation, running progress, or result view of the update."""
        del stats
        del title_font
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
        if self.phase == "confirm":
            lines = (
                *wrap_text("Descarga el codigo con git pull --ff-only.", 34),
                *wrap_text("Los pasos con sudo se indican al terminar.", 34),
                "A: ACTUALIZAR   B: VOLVER",
            )
            for index, line in enumerate(lines):
                color = theme.ACCENT_COLOR if index == len(lines) - 1 else theme.TEXT_COLOR
                surface.blit(render_cached(small_font, line, color), (16, 36 + index * 13))
        elif self.phase == "running":
            elapsed = max(0, int(time.monotonic() - self.started_at)) if self.started_at else 0
            dots = "." * (elapsed % 4)
            surface.blit(
                render_cached(body_font, f"ACTUALIZANDO{dots}", theme.TEXT_COLOR), (16, 36)
            )
            surface.blit(
                render_cached(
                    small_font, f"Esperando git: {elapsed}s (max. 180s)", theme.ACCENT_COLOR
                ),
                (16, 56),
            )
            for index, line in enumerate(processes.output.splitlines()[-3:]):
                surface.blit(
                    render_cached(small_font, plain_text(line)[:34], theme.TEXT_COLOR),
                    (16, 76 + index * 16),
                )
            self._draw_progress(surface)
            surface.blit(
                render_cached(small_font, "B CANCELA LA DESCARGA.", theme.ACCENT_COLOR), (16, 194)
            )
        else:
            lines = self._result_lines(processes)
            self.result_view.update(len(lines))
            for position, index in enumerate(range(self.result_view.first, self.result_view.last)):
                color = theme.ACCENT_COLOR if index == 0 else theme.TEXT_COLOR
                surface.blit(
                    render_cached(small_font, lines[index], color),
                    (16, RESULT_TOP + position * RESULT_ROW),
                )
            draw_scroll_indicator(
                surface,
                pygame.Rect(12, RESULT_TOP, 296, RESULT_BOTTOM - RESULT_TOP),
                self.result_view.has_above,
                self.result_view.has_below,
                theme.ACCENT_COLOR,
            )

    def _result_lines(self, processes: ProcessManager) -> list[str]:
        """Build wrapped status and captured output lines for the result view."""
        lines = wrap_text(processes.message, 34)
        for line in processes.output.splitlines():
            lines.extend(wrap_text(line, 34))
        return lines

    def _draw_progress(self, surface: pygame.Surface) -> None:
        """Draw a hard-edged indeterminate marker because git reports no percentage."""
        pygame.draw.rect(surface, theme.MUTED_COLOR, (15, 145, 290, 7))
        position = 15 + int((self.activity * 70) % 270)
        pygame.draw.rect(surface, theme.ACCENT_COLOR, (position, 145, 20, 7))

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return button labels for the current update-screen state."""
        if self.phase == "confirm":
            return [("A ACTUALIZAR", 12), ("B VOLVER", 168)]
        if self.phase == "running":
            return [("B CANCELAR", 12)]
        return [("ARR/ABA TEXTO", 8), ("A/B VOLVER", 150)]
