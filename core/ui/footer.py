import pygame

from core import theme


def draw_footer(
    surface: pygame.Surface,
    font: pygame.font.Font,
    hints: list[tuple[str, int]] | None = None,
) -> None:
    """Draw the bottom separator and action hints for the current screen."""
    pygame.draw.line(surface, theme.ORANGE, (20, 425), (620, 425), 2)
    labels = hints or [
        ("D-PAD MOVER", 24),
        ("A ABRIR", 180),
        ("B VOLVER", 325),
        ("START DETALLE", 465),
    ]
    for label, x in labels:
        surface.blit(font.render(label, True, theme.ORANGE), (x, 444))
