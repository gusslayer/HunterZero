"""Draw the bottom action bar with boxed key hints for the current screen."""

import pygame

from core import theme
from core.ui.text_cache import render_cached
from core.ui.widgets import draw_keycap, plain_text


def draw_footer(
    surface: pygame.Surface,
    font: pygame.font.Font,
    hints: list[tuple[str, int]] | None = None,
) -> None:
    """Draw the bottom separator and boxed key hints for the current screen."""
    pygame.draw.rect(surface, theme.PANEL_COLOR, (0, 211, theme.WIDTH, 29))
    pygame.draw.line(surface, theme.MUTED_COLOR, (10, 211), (310, 211), 1)
    labels = hints or [
        ("D-PAD MOVER", 12),
        ("A ABRIR", 104),
        ("B VOLVER", 168),
        ("START", 248),
    ]
    for label, x in labels:
        parts = plain_text(label).split(" ", 1)
        key_width = draw_keycap(surface, font, parts[0], x, 221, theme.ACCENT_COLOR)
        if len(parts) > 1:
            caption = render_cached(font, parts[1], theme.TEXT_COLOR)
            surface.blit(caption, (x + key_width + 5, 223))
