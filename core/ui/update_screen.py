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

    def handle(self, action, processes: ProcessManager) -> bool:
        """Start the update on OPEN, cancel on BACK, and exit when finished."""
        if self.phase == "confirm":
            if action == OPEN:
                if not processes.start_update():
                    self.phase = "result"
                    return False
                self.started_at = time.monotonic()
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
        """Move to the result view when the update process finishes."""
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
        surface.fill(theme.BLACK)
        surface.blit(title_font.render(self.title, True, theme.ORANGE), (30, 72))
        if self.phase == "confirm":
            lines = (
                "Descarga el código con git pull --ff-only.",
                "Los pasos que necesitan sudo se indican al terminar.",
                "A: actualizar    B: volver",
            )
        elif self.phase == "running":
            elapsed = int(time.monotonic() - self.started_at) if self.started_at else 0
            dots = "." * (elapsed % 4)
            lines = (
                f"ACTUALIZANDO HUNTERZERO{dots}",
                f"Tiempo: {elapsed}s / 180s",
                *[line[:46] for line in processes.output.splitlines()[-2:]],
                "B cancela la descarga.",
            )
        else:
            lines = tuple([processes.message[:46], *processes.output.splitlines()[-6:]])
        for index, line in enumerate(lines):
            color = theme.AMBER if index == 0 else theme.WHITE
            surface.blit(small_font.render(line[:46], True, color), (30, 132 + index * 44))
        if self.phase == "running":
            self._draw_progress(surface, elapsed)

    def _draw_progress(self, surface: pygame.Surface, elapsed: int) -> None:
        """Draw a bounded progress bar for the update's maximum duration."""
        pygame.draw.rect(surface, theme.DIM_ORANGE, (30, 350, 580, 12))
        ratio = min(1.0, elapsed / 180)
        pygame.draw.rect(surface, theme.ORANGE, (30, 350, int(580 * ratio), 12))

    def footer_hints(self) -> list[tuple[str, int]]:
        """Return button labels for the current update-screen state."""
        if self.phase == "confirm":
            return [("A ACTUALIZAR", 24), ("B VOLVER", 335)]
        if self.phase == "running":
            return [("B CANCELAR", 24)]
        return [("A/B VOLVER", 24)]
