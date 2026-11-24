"""Reusable gamepad help view shared by independently implemented modules."""

import pygame

from core import theme


def draw_help_view(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    small_font: pygame.font.Font,
    title: str,
    sections: tuple[tuple[str, tuple[str, ...]], ...],
) -> None:
    """Render titled help sections with wrapped text and common button guidance."""
    pygame.draw.rect(surface, theme.BLACK, (0, 55, theme.WIDTH, 370))
    surface.blit(title_font.render(title[:23], True, theme.ORANGE), (28, 72))
    y = 118
    for heading, paragraphs in sections:
        if y >= 350:
            break
        surface.blit(body_font.render(heading[:30], True, theme.AMBER), (30, y))
        y += body_font.get_linesize() + 8
        for paragraph in paragraphs:
            for line in _wrap_text(paragraph, small_font, 570):
                if y >= 356:
                    break
                surface.blit(small_font.render(line, True, theme.WHITE), (30, y))
                y += small_font.get_linesize() + 6
            y += 4
    surface.blit(
        small_font.render("A: volver    B: salir", True, theme.ORANGE),
        (30, 388),
    )


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap one help paragraph into lines that fit the GPi content area."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]
