"""Screen that runs the repository update flow from the main menu."""

import time

import pygame

from core import theme
from core.input import BACK, OPEN
from core.process_manager import ProcessManager


class UpdateScreen:
    """Guide the user through running deploy/update.sh with captured output."""

    def __init__(self) -> None:
        """Start the screen on the confirmation phase."""
        self.title = "ACTUALIZAR HUNTERZERO"
        self.phase = "confirm"
        self.started_at = 0.0
        self.last_sync = 0.0
        self.activity = 0.0

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
        pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
        surface.blit(title_font.render(self.title[:18], False, theme.ACCENT_COLOR), (15, 36))
        if self.phase == "confirm":
            lines = (
                "Descarga el codigo con git pull --ff-only.",
                "Los pasos con sudo se indican al terminar.",
                "A: actualizar    B: volver",
            )
            for index, line in enumerate(lines):
                surface.blit(small_font.render(line[:36], False, theme.TEXT_COLOR), (15, 66 + index * 20))
        elif self.phase == "running":
            elapsed = max(0, int(time.monotonic() - self.started_at)) if self.started_at else 0
            dots = "." * (elapsed % 4)
            surface.blit(
                body_font.render(f"ACTUALIZANDO{dots}", False, theme.TEXT_COLOR), (15, 59)
            )
            surface.blit(
                small_font.render(f"Esperando git: {elapsed}s (max. 180s)", False, theme.ACCENT_COLOR),
                (15, 78),
            )
            for index, line in enumerate(processes.output.splitlines()[-3:]):
                surface.blit(small_font.render(line[:36], False, theme.TEXT_COLOR), (15, 98 + index * 16))
            self._draw_progress(surface)
            surface.blit(small_font.render("B CANCELA LA DESCARGA.", False, theme.ACCENT_COLOR), (15, 194))
        else:
            lines = (processes.message[:40], *processes.output.splitlines()[-6:])
            for index, line in enumerate(lines):
                color = theme.ACCENT_COLOR if index == 0 else theme.TEXT_COLOR
                surface.blit(small_font.render(line[:36], False, color), (15, 62 + index * 18))

    def _draw_progress(self, surface: pygame.Surface) -> None:
        """Draw a hard-edged indeterminate marker because git reports no percentage."""
        pygame.draw.rect(surface, theme.MUTED_COLOR, (15, 165, 290, 7))
        position = 15 + int((self.activity * 70) % 270)
        pygame.draw.rect(surface, theme.ACCENT_COLOR, (position, 165, 20, 7))

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return button labels for the current update-screen state."""
        if self.phase == "confirm":
            return [("A ACTUALIZAR", 12), ("B VOLVER", 168)]
        if self.phase == "running":
            return [("B CANCELAR", 12)]
        return [("A/B VOLVER", 12)]
