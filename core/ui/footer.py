import pygame

from core import theme


def draw_footer(surface: pygame.Surface, font: pygame.font.Font) -> None:
    pygame.draw.line(surface, theme.ORANGE, (20, 425), (620, 425), 2)
    hints = [("D-PAD MOVER", 24), ("A ABRIR", 190), ("B VOLVER", 335), ("START EJECUTAR", 485)]
    for label, x in hints:
        surface.blit(font.render(label, True, theme.ORANGE), (x, 444))
