"""Reusable gamepad help view shared by independently implemented modules."""

import pygame

from core import theme
from core.ui.text_cache import render_cached
from core.ui.widgets import plain_text


def draw_help_view(
    surface: pygame.Surface,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    small_font: pygame.font.Font,
    title: str,
    sections: tuple[tuple[str, tuple[str, ...]], ...],
) -> None:
    """Render titled help sections with wrapped text and common button guidance."""
    del title_font
    pygame.draw.rect(surface, theme.BG_COLOR, (0, 28, theme.WIDTH, 184))
    y = 36
    for heading, paragraphs in sections:
        if y >= 175:
            break
        surface.blit(render_cached(body_font, plain_text(heading)[:30], theme.ACCENT_COLOR), (16, y))
        y += body_font.get_linesize() + 4
        for paragraph in paragraphs:
            for line in _wrap_text(paragraph, small_font, 285):
                if y >= 178:
                    break
                surface.blit(render_cached(small_font, line, theme.TEXT_COLOR), (16, y))
                y += small_font.get_linesize() + 3
            y += 2
    surface.blit(
        render_cached(small_font, "A: VOLVER   B: SALIR", theme.ACCENT_COLOR), (16, 194)
    )


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap one help paragraph into lines that fit the GPi content area."""
    lines: list[str] = []
    current = ""
    for word in plain_text(text).split():
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]
