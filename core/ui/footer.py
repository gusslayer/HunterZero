import pygame

from core import theme
from core.ui.text_cache import render_cached


def draw_footer(
    surface: pygame.Surface,
    font: pygame.font.Font,
    hints: list[tuple[str, int]] | None = None,
) -> None:
    """Draw the bottom separator and action hints for the current screen."""
    pygame.draw.line(surface, theme.MUTED_COLOR, (10, 212), (310, 212), 1)
    labels = hints or [
        ("D-PAD MOVER", 12),
        ("A ABRIR", 104),
        ("B VOLVER", 168),
        ("START", 248),
    ]
    for label, x in labels:
        surface.blit(render_cached(font, label, theme.ACCENT_COLOR), (x, 222))
